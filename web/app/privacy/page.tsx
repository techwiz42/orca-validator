const wrap: React.CSSProperties = { maxWidth: 760, margin: "0 auto", padding: 24, lineHeight: 1.6 };

export default function Privacy() {
  return (
    <main style={wrap}>
      <h1>Privacy Notice</h1>
      <p style={{ color: "#8b949e" }}>
        ORCA Validator is <strong>experimental demonstration software</strong>. Please read this
        before uploading anything.
      </p>

      <h2>What happens to a document you upload</h2>
      <ul>
        <li>Your file is parsed on our server (OCR / text extraction).</li>
        <li>
          <strong>
            The extracted text is sent to a third-party AI provider (Together AI) to generate the
            analysis and the proposed revised document.
          </strong>{" "}
          It leaves our server and is processed under Together AI&rsquo;s own terms and privacy policy.
        </li>
        <li>
          Uploaded files and results are stored on the server for the demo and may appear in server
          logs for debugging. We do <strong>not</strong> guarantee deletion, retention limits, or
          confidentiality.
        </li>
      </ul>

      <h2 style={{ color: "#f85149" }}>Do not upload confidential or sensitive documents</h2>
      <p>
        Do not upload anything confidential, privileged, personal (PII), regulated (health,
        financial), trade-secret, or that you are not authorized to disclose to third parties. Use
        synthetic or non-sensitive documents only. You upload at your own risk.
      </p>

      <h2>Tracking</h2>
      <p>The site sets no advertising or analytics cookies.</p>

      <p style={{ marginTop: 32 }}>
        <a href="/" style={{ color: "#58a6ff" }}>&larr; back to the app</a>
        {"  ·  "}
        <a href="/tos" style={{ color: "#58a6ff" }}>Terms of Service</a>
      </p>
    </main>
  );
}
