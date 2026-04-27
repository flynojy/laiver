import { ArrowUpRight } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function StatCard({
  title,
  value,
  description
}: {
  title: string;
  value: string;
  description: string;
}) {
  return (
    <Card className="bg-white/90">
      <CardHeader className="pb-3">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="flex items-center justify-between text-3xl">
          {value}
          <ArrowUpRight className="h-5 w-5 text-[var(--muted-foreground)]" />
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 text-sm text-[var(--muted-foreground)]">{description}</CardContent>
    </Card>
  );
}

