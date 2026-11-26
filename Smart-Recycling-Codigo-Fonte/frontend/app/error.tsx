"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section className="error-panel" role="alert">
      <h1>Não foi possível carregar os dados.</h1>
      <p>Verifique a conexão com a central e tente novamente.</p>
      <button onClick={reset}>Tentar novamente</button>
    </section>
  );
}
