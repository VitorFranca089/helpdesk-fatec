export function BlocoJson({ titulo, dados, aberto = false }: { titulo: string; dados: unknown; aberto?: boolean }) {
  return (
    <details className="bloco-json" open={aberto}>
      <summary>{titulo}</summary>
      <pre>{JSON.stringify(dados, null, 2)}</pre>
    </details>
  );
}
