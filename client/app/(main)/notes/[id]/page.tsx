import { headers } from "next/headers";
import { fetchAPI, getToken } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface Note {
  id: string;
  topic: string;
  content: string;
  summary: string;
}

interface Feedback {
  id: string;
  understanding_level: string;
  strength: string;
  improvements: string;
  created_at: string;
}

export default async function NotePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieHeader = (await headers()).get("cookie") ?? "";
  const token = await getToken(cookieHeader);
  const [note, { feedbacks }] = await Promise.all([
    fetchAPI(`/api/notes/${id}`, { token }) as Promise<Note>,
    fetchAPI(`/api/notes/${id}/feedbacks`, { token }) as Promise<{
      feedbacks: Feedback[];
    }>,
  ]);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-6 py-8">
        <h1 className="mb-6 text-2xl font-bold">学習ノート</h1>

        <Tabs defaultValue="note">
          <TabsList className="mb-6">
            <TabsTrigger value="note">ノート</TabsTrigger>
            <TabsTrigger value="feedback">フィードバック</TabsTrigger>
          </TabsList>

          <TabsContent value="note">
            <Card>
              <CardContent className="space-y-6 p-6">
                <section>
                  <h2 className="mb-2 text-sm font-medium text-muted-foreground">
                    トピック
                  </h2>
                  <p className="text-lg font-semibold">{note.topic}</p>
                </section>

                <section>
                  <h2 className="mb-2 text-sm font-medium text-muted-foreground">
                    要約
                  </h2>
                  <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed">
                    {note.summary.split("\n").map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                </section>

                <section>
                  <h2 className="mb-2 text-sm font-medium text-muted-foreground">
                    内容
                  </h2>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {note.content}
                  </div>
                </section>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="feedback">
            {feedbacks.length === 0 ? (
              <Card>
                <CardContent className="p-6 text-center text-sm text-muted-foreground">
                  フィードバックはまだありません
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {feedbacks.map((fb) => (
                  <Card key={fb.id}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">
                        理解度: {fb.understanding_level}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 px-6 pb-6">
                      <section>
                        <h3 className="mb-1 text-sm font-medium text-muted-foreground">
                          強み
                        </h3>
                        <p className="text-sm leading-relaxed">{fb.strength}</p>
                      </section>
                      <section>
                        <h3 className="mb-1 text-sm font-medium text-muted-foreground">
                          改善点
                        </h3>
                        <p className="text-sm leading-relaxed">
                          {fb.improvements}
                        </p>
                      </section>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
