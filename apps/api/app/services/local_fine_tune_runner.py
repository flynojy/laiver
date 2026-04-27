from __future__ import annotations

import importlib
import importlib.util
import json
import os
import platform
from pathlib import Path
from typing import Any


DEFAULT_MAX_LENGTH = 1024


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        rows.append(json.loads(text))
    return rows


def _mock_training_enabled(config: dict[str, Any]) -> bool:
    flag = os.getenv("LAIVER_FINE_TUNE_MOCK", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    base_model = str(config.get("base_model", "")).strip().lower()
    return base_model.startswith("mock://")


def _render_prompt(messages: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = str(message.get("role", "user")).strip().lower()
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"<|{role}|>\n{content}")
    lines.append("<|assistant|>\n")
    return "\n".join(lines)


def _check_dependencies(backend: str) -> list[str]:
    required = ["torch", "transformers", "peft", "accelerate"]
    if backend == "local_qlora":
        required.append("bitsandbytes")
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    return missing


def _load_module(name: str) -> Any:
    return importlib.import_module(name)


def _supports_bfloat16(torch_module: Any) -> bool:
    if not torch_module.cuda.is_available():
        return False
    if not hasattr(torch_module.cuda, "is_bf16_supported"):
        return False
    return bool(torch_module.cuda.is_bf16_supported())


def _infer_target_modules(model: Any) -> list[str]:
    preferred = [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
        "query_key_value",
        "Wqkv",
    ]
    available = {name.rsplit(".", 1)[-1] for name, _ in model.named_modules()}
    selected = [name for name in preferred if name in available]
    return selected or ["q_proj", "v_proj"]


def _build_training_examples(
    *,
    dataset_path: Path,
    tokenizer: Any,
    max_length: int,
    dataset_label: str,
) -> list[dict[str, list[int]]]:
    rows = _read_jsonl(dataset_path)
    examples: list[dict[str, list[int]]] = []
    eos_token = tokenizer.eos_token or ""

    for sample in rows:
        messages = sample.get("messages")
        if not isinstance(messages, list) or len(messages) < 2:
            continue

        prompt_messages = messages[:-1]
        target_message = messages[-1]
        if str(target_message.get("role", "")).lower() != "assistant":
            continue

        target_text = str(target_message.get("content", "")).strip()
        if not target_text:
            continue

        prompt_text = _render_prompt(prompt_messages)
        full_text = f"{prompt_text}{target_text}{eos_token}"

        prompt_ids = tokenizer(
            prompt_text,
            add_special_tokens=False,
            truncation=True,
            max_length=max_length,
        )["input_ids"]
        tokenized = tokenizer(
            full_text,
            add_special_tokens=False,
            truncation=True,
            max_length=max_length,
        )

        input_ids = list(tokenized["input_ids"])
        attention_mask = list(tokenized["attention_mask"])
        labels = list(input_ids)

        prompt_token_count = min(len(input_ids), len(prompt_ids))
        if prompt_token_count >= len(labels):
            continue

        labels[:prompt_token_count] = [-100] * prompt_token_count
        if all(token == -100 for token in labels):
            continue

        examples.append(
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "labels": labels,
            }
        )

    if not examples:
        raise RuntimeError(f"The {dataset_label} split did not produce any trainable samples.")

    return examples


def _run_mock_training(config: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(config["output_dir"])
    artifact_dir = output_dir / "final_adapter"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "mode": "mock",
        "artifact_path": artifact_dir.as_posix(),
        "metrics": {
            "train_samples": plan["split_counts"]["train"],
            "validation_samples": plan["split_counts"]["validation"],
            "test_samples": plan["split_counts"]["test"],
            "epochs": plan["hyperparameters"]["num_train_epochs"],
        },
        "backend": plan["backend"],
        "base_model": plan["base_model"],
    }

    _write_json(artifact_dir / "adapter_config.json", result)
    (artifact_dir / "README.md").write_text(
        "# Laiver mock adapter\n\nThis artifact was generated by the local mock training path.\n",
        encoding="utf-8",
    )
    _write_json(output_dir / "training_result.json", result)
    return result


def _run_transformers_training(config: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    torch = _load_module("torch")
    transformers = _load_module("transformers")
    peft = _load_module("peft")

    if plan["backend"] == "local_qlora" and platform.system() == "Windows":
        raise RuntimeError("QLoRA training currently requires a Linux or WSL environment with bitsandbytes support.")

    hyperparameters = plan["hyperparameters"]
    base_model = plan["base_model"]
    max_length = int(hyperparameters["max_length"])
    output_dir = Path(config["output_dir"])

    tokenizer = transformers.AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({"pad_token": "<pad>"})

    load_kwargs: dict[str, Any] = {"trust_remote_code": True}
    if torch.cuda.is_available():
        load_kwargs["device_map"] = "auto"
        load_kwargs["torch_dtype"] = torch.bfloat16 if _supports_bfloat16(torch) else torch.float16
    else:
        load_kwargs["torch_dtype"] = torch.float32

    if plan["backend"] == "local_qlora":
        bitsandbytes_config = transformers.BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16 if _supports_bfloat16(torch) else torch.float16,
        )
        load_kwargs["quantization_config"] = bitsandbytes_config

    model = transformers.AutoModelForCausalLM.from_pretrained(base_model, **load_kwargs)
    if tokenizer.vocab_size != model.get_input_embeddings().weight.shape[0]:
        model.resize_token_embeddings(len(tokenizer))

    if plan["backend"] == "local_qlora" and hasattr(peft, "prepare_model_for_kbit_training"):
        model = peft.prepare_model_for_kbit_training(model)

    target_modules = _infer_target_modules(model)
    peft_config = peft.LoraConfig(
        r=int(hyperparameters["lora_r"]),
        lora_alpha=int(hyperparameters["lora_alpha"]),
        lora_dropout=float(hyperparameters["lora_dropout"]),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target_modules,
    )
    model = peft.get_peft_model(model, peft_config)
    model.config.use_cache = False

    train_dataset = _build_training_examples(
        dataset_path=Path(config["dataset"]["train_path"]),
        tokenizer=tokenizer,
        max_length=max_length,
        dataset_label="train",
    )
    validation_rows = _read_jsonl(Path(config["dataset"]["validation_path"]))
    validation_dataset = None
    if validation_rows:
        validation_dataset = _build_training_examples(
            dataset_path=Path(config["dataset"]["validation_path"]),
            tokenizer=tokenizer,
            max_length=max_length,
            dataset_label="validation",
        )

    class ConversationDataset(torch.utils.data.Dataset):
        def __init__(self, rows: list[dict[str, list[int]]]) -> None:
            self.rows = rows

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, index: int) -> dict[str, list[int]]:
            return self.rows[index]

    training_args = transformers.TrainingArguments(
        output_dir=output_dir.as_posix(),
        overwrite_output_dir=True,
        num_train_epochs=float(hyperparameters["num_train_epochs"]),
        per_device_train_batch_size=int(hyperparameters["per_device_train_batch_size"]),
        per_device_eval_batch_size=int(hyperparameters["per_device_eval_batch_size"]),
        gradient_accumulation_steps=int(hyperparameters["gradient_accumulation_steps"]),
        learning_rate=float(hyperparameters["learning_rate"]),
        warmup_ratio=float(hyperparameters["warmup_ratio"]),
        logging_steps=int(hyperparameters["logging_steps"]),
        evaluation_strategy="epoch" if validation_dataset else "no",
        save_strategy="epoch",
        save_total_limit=1,
        report_to=[],
        remove_unused_columns=False,
        fp16=torch.cuda.is_available() and not _supports_bfloat16(torch),
        bf16=_supports_bfloat16(torch),
    )

    trainer = transformers.Trainer(
        model=model,
        args=training_args,
        train_dataset=ConversationDataset(train_dataset),
        eval_dataset=ConversationDataset(validation_dataset) if validation_dataset else None,
        data_collator=transformers.DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True),
    )
    train_result = trainer.train()
    metrics = dict(train_result.metrics)
    if validation_dataset:
        metrics.update(trainer.evaluate())

    artifact_dir = output_dir / "final_adapter"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(artifact_dir.as_posix())
    tokenizer.save_pretrained(artifact_dir.as_posix())

    result = {
        "mode": "transformers",
        "artifact_path": artifact_dir.as_posix(),
        "metrics": metrics,
        "backend": plan["backend"],
        "base_model": plan["base_model"],
        "target_modules": target_modules,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
    }
    _write_json(output_dir / "training_result.json", result)
    return result


def build_training_plan(config: dict[str, Any]) -> dict[str, Any]:
    hyperparameters = dict(config.get("hyperparameters") or {})
    hyperparameters.setdefault("max_length", DEFAULT_MAX_LENGTH)
    hyperparameters.setdefault("num_train_epochs", 1)
    hyperparameters.setdefault("learning_rate", 2e-4)
    hyperparameters.setdefault("per_device_train_batch_size", 1)
    hyperparameters.setdefault("per_device_eval_batch_size", 1)
    hyperparameters.setdefault("gradient_accumulation_steps", 4)
    hyperparameters.setdefault("warmup_ratio", 0.03)
    hyperparameters.setdefault("logging_steps", 1)
    hyperparameters.setdefault("lora_r", 16)
    hyperparameters.setdefault("lora_alpha", 32)
    hyperparameters.setdefault("lora_dropout", 0.05)

    split_counts = {
        "train": len(_read_jsonl(Path(config["dataset"]["train_path"]))),
        "validation": len(_read_jsonl(Path(config["dataset"]["validation_path"]))),
        "test": len(_read_jsonl(Path(config["dataset"]["test_path"]))),
    }

    return {
        "job_id": config["job_id"],
        "name": config["name"],
        "backend": config["backend"],
        "base_model": config["base_model"],
        "source_speaker": config["source_speaker"],
        "output_dir": config["output_dir"],
        "hyperparameters": hyperparameters,
        "split_counts": split_counts,
        "execution_mode": "mock" if _mock_training_enabled(config) else "transformers",
        "dependency_status": {
            "missing": _check_dependencies(str(config.get("backend", ""))),
            "platform": platform.system(),
        },
    }


def run_training_job(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Job config not found: {config_path}")

    config = _read_json(config_path)
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    plan = build_training_plan(config)
    _write_json(output_dir / "training_plan.json", plan)

    if _mock_training_enabled(config):
        return _run_mock_training(config, plan)

    missing = plan["dependency_status"]["missing"]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            "Local fine-tuning dependencies are missing: "
            f"{joined}. Install the API package with the local-training extras first."
        )

    return _run_transformers_training(config, plan)
