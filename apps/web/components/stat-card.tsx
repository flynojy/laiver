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
    <Card>
      <CardHeader className="pb-2">
        <CardDescription className="text-xs">{title}</CardDescription>
        <CardTitle className="text-2xl font-medium">{value}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0 text-xs leading-5 text-[var(--muted-foreground)]">
        {description}
      </CardContent>
    </Card>
  );
}
