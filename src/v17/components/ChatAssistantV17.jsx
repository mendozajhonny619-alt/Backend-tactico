import React, { useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.REACT_APP_API_URL ||
  "http://127.0.0.1:8000";

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function buildCompactSnapshot(data) {
  return {
    version: data?.version || "V17",
    updated_at: data?.updated_at || null,
    message: data?.message || null,
    summary: data?.summary || {},
    top_signals: safeArray(data?.top_signals),
    observe: safeArray(data?.observe),
    no_bet: safeArray(data?.no_bet),
    blocked: safeArray(data?.blocked),
    all_analyzed: safeArray(data?.all_analyzed),
    pending_signals: safeArray(data?.pending_signals),
    performance_analysis: data?.performance_analysis || {},
  };
}

function quickQuestions() {
  return [
    "¿Qué partido ves mejor ahora?",
    "¿Hay alguna señal lista o solo candidatos?",
    "¿Qué candidato necesita confirmación?",
    "¿Qué partidos debo ignorar?",
    "¿Cuál lectura domina ahora, OVER o UNDER?",
    "¿Qué está bloqueado y por qué?",
  ];
}

export default function ChatAssistantV17({ data, selectedMatch = null }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Estoy listo para analizar el panel V17. Puedes preguntarme qué partido veo mejor, por qué una señal está en espera o qué lectura domina.",
    },
  ]);

  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("quick");
  const [loading, setLoading] = useState(false);
  const [lastModel, setLastModel] = useState(null);
  const [usedOpenAI, setUsedOpenAI] = useState(false);
  const [error, setError] = useState("");

  const dashboardSnapshot = useMemo(() => buildCompactSnapshot(data || {}), [data]);

  async function askAssistant(customQuestion) {
    const finalQuestion = String(customQuestion || question || "").trim();

    if (!finalQuestion || loading) {
      return;
    }

    setError("");
    setQuestion("");

    const userMessage = {
      role: "user",
      content: finalQuestion,
    };

    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/v17/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: finalQuestion,
          dashboard_snapshot: dashboardSnapshot,
          selected_match: selectedMatch,
          mode,
          conversation: nextMessages.slice(-8),
        }),
      });

      if (!response.ok) {
        throw new Error(`Error HTTP ${response.status}`);
      }

      const payload = await response.json();

      setLastModel(payload?.model || null);
      setUsedOpenAI(Boolean(payload?.used_openai));

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            payload?.answer ||
            "El asistente respondió, pero no se recibió contenido válido.",
        },
      ]);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No se pudo conectar con el asistente.";

      setError(message);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "No pude conectar con el asistente V17 en este momento. Revisa que el backend esté activo y que exista POST /v17/chat.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    askAssistant();
  }

  return (
    <section className="v17-chat-panel">
      <div className="v17-chat-header">
        <div>
          <span>JHONNY ELITE ASSISTANT</span>
          <h2>Chat IA V17</h2>
          <p>
            Conversa con el sistema sobre señales, candidatos, bloqueos, OVER,
            UNDER, riesgo y momento de entrada.
          </p>
        </div>

        <div className="v17-chat-status">
          <strong>{usedOpenAI ? "IA EXTERNA" : "MODO LOCAL"}</strong>
          <small>{lastModel || "LOCAL_FALLBACK"}</small>
        </div>
      </div>

      <div className="v17-chat-mode-row">
        <button
          type="button"
          className={mode === "quick" ? "active" : ""}
          onClick={() => setMode("quick")}
        >
          Rápido
        </button>

        <button
          type="button"
          className={mode === "deep" ? "active" : ""}
          onClick={() => setMode("deep")}
        >
          Análisis profundo
        </button>

        <button
          type="button"
          className={mode === "audit" ? "active" : ""}
          onClick={() => setMode("audit")}
        >
          Auditoría
        </button>
      </div>

      <div className="v17-chat-quick">
        {quickQuestions().map((item) => (
          <button key={item} type="button" onClick={() => askAssistant(item)}>
            {item}
          </button>
        ))}
      </div>

      <div className="v17-chat-messages">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`v17-chat-message ${message.role}`}
          >
            <span>{message.role === "user" ? "Tú" : "V17 Assistant"}</span>
            <p>{message.content}</p>
          </div>
        ))}

        {loading ? (
          <div className="v17-chat-message assistant">
            <span>V17 Assistant</span>
            <p>Analizando el panel y preparando respuesta...</p>
          </div>
        ) : null}
      </div>

      {error ? <div className="v17-chat-error">{error}</div> : null}

      <form className="v17-chat-form" onSubmit={handleSubmit}>
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Pregúntale al sistema, por ejemplo: ¿este UNDER ya sirve o espero?"
        />

        <button type="submit" disabled={loading}>
          {loading ? "Analizando..." : "Enviar"}
        </button>
      </form>
    </section>
  );
                      }
