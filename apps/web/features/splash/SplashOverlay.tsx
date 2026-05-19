"use client";

import { ATFieldBurst } from "@/components/glyphs/ATFieldBurst";
import { HexGrid } from "@/components/glyphs/HexGrid";
import { NervMark } from "@/components/glyphs/NervMark";
import { CornerBrackets } from "@/features/splash/CornerBrackets";
import { Mask02Extended } from "@/features/splash/Mask02Extended";
import { useSplashState } from "@/features/splash/useSplashState";
import { useI18n } from "@/features/i18n/language-provider";

import styles from "./splash.module.css";

/**
 * The 4.2s NERV / EVA-02 opening sequence. Timing is driven entirely by
 * CSS `animation-delay`, so the React tree just declares the elements
 * once. `useSplashState` listens for skip gestures and the auto-dismiss
 * timer, then transitions `phase` through playing → dismissing → done.
 */
export function SplashOverlay() {
  const { phase, dismiss } = useSplashState(4200);
  const { t } = useI18n();

  if (phase === "done") return null;

  return (
    <div
      className={[styles.overlay, phase === "dismissing" ? styles.fadingOut : ""]
        .filter(Boolean)
        .join(" ")}
      role="presentation"
      aria-label="LAIVER intro"
    >
      {/* Background hex grid */}
      <div className={styles.hexBg}>
        <HexGrid />
      </div>

      {/* Top scanline that drops down */}
      <div className={styles.scanline} />

      {/* Four corner brackets */}
      <CornerBrackets className={styles.bracket} />

      {/* Top-left boot text */}
      <div className={styles.bootText}>
        ▶ {t("INITIATING NERV TERMINAL")}
        <span className={styles.caret}>_</span>
      </div>

      {/* Bottom-left MAGI status */}
      <div className={styles.magiStatus}>
        MAGI <span className={styles.magiDot}>●</span> CASPER{" "}
        <span className={styles.magiDot}>●</span> MELCHIOR{" "}
        <span className={styles.magiDot}>●</span> BALTHASAR
      </div>

      {/* AT FIELD concentric hexagons */}
      <div className={styles.atField}>
        <ATFieldBurst />
      </div>
      <div className={styles.atFieldFlash} />
      <div className={styles.atFieldText}>{t("AT FIELD · ACTIVATED")}</div>

      {/* EVA-02 mask + shoulders (the key beat) */}
      <div className={styles.evaMask}>
        <Mask02Extended eyeClassName={styles.eyeSlit} />
      </div>

      {/* Top-right sync ratio */}
      <div className={styles.syncRatio}>
        <span className={styles.syncLabel}>{t("SYNC RATIO")}</span>
        <span className={styles.syncValue}>87.4%</span>
      </div>

      {/* Bottom-right NERV mark */}
      <div className={styles.nervMark}>
        <NervMark />
      </div>

      {/* Bottom-center brand */}
      <div className={styles.brand}>
        <div className={styles.brandMain}>LAIVER</div>
        <div className={styles.brandSub}>/ EVA-02 EDITION</div>
      </div>

      {/* Bottom-center system online (brief, before dismiss) */}
      <div className={styles.systemOnline}>● {t("SYSTEM ONLINE")}</div>

      {/* Skip hint */}
      <button
        type="button"
        className={styles.skipHint}
        onClick={(event) => {
          event.stopPropagation();
          dismiss();
        }}
      >
        [ESC] {t("SKIP")}
      </button>
    </div>
  );
}
