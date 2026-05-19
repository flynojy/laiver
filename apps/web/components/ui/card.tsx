"use client";

import * as React from "react";

import { useI18n } from "@/features/i18n/language-provider";
import { cn } from "@/lib/utils";

type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  notched?: boolean;
};

export function Card({ className, notched = false, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "relative rounded-[12px] border border-[color:var(--border)] bg-[var(--surface)] shadow-panel",
        notched && "nerv-notch",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-2 p-6", className)} {...props} />;
}

export function CardTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  const { tNode } = useI18n();

  return (
    <h3
      className={cn(
        "text-base font-semibold tracking-tight text-[var(--foreground)]",
        className
      )}
      {...props}
    >
      {tNode(props.children)}
    </h3>
  );
}

export function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  const { tNode } = useI18n();

  return (
    <p
      className={cn("text-xs leading-5 text-[var(--foreground-muted)]", className)}
      {...props}
    >
      {tNode(props.children)}
    </p>
  );
}

export function CardContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const { tNode } = useI18n();

  return (
    <div className={cn("px-6 pb-6", className)} {...props}>
      {tNode(props.children)}
    </div>
  );
}
