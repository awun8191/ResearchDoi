import { Link } from 'react-router-dom';

export default function NotFound() {
  const currentUser = { uid: "localUser" };
  const primaryHref = currentUser ? '/projects' : '/';

  return (
    <section className="nf-wrap">
      <div className="nf-card">
        <p className="nf-code">404</p>
        <h1 className="nf-title">Page not found</h1>
        <p className="nf-text">
          The page you requested does not exist or may have moved.
        </p>
        <div className="nf-actions">
          <Link className="nf-btn nf-btn-primary" to={primaryHref}>
            {currentUser ? 'Go to Projects' : 'Go to Login'}
          </Link>
          <Link className="nf-btn nf-btn-ghost" to="/">
            Go Home
          </Link>
        </div>
      </div>
      <style>{styles}</style>
    </section>
  );
}

const styles = `
  .nf-wrap {
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 2rem;
  }

  .nf-card {
    width: min(680px, 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    background:
      radial-gradient(circle at 20% 20%, color-mix(in srgb, var(--secondary) 16%, transparent), transparent 40%),
      var(--bg-surface);
    box-shadow: var(--shadow-lg);
    padding: 2rem;
    text-align: center;
  }

  .nf-code {
    font-family: var(--font-mono);
    font-size: clamp(2rem, 5vw, 3rem);
    letter-spacing: 0.08em;
    color: var(--secondary);
    margin-bottom: 0.25rem;
  }

  .nf-title {
    font-size: clamp(1.5rem, 3.5vw, 2.25rem);
    color: var(--text-main);
    margin-bottom: 0.75rem;
  }

  .nf-text {
    color: var(--text-muted);
    max-width: 48ch;
    margin: 0 auto 1.5rem;
    line-height: 1.5;
  }

  .nf-actions {
    display: flex;
    gap: 0.75rem;
    justify-content: center;
    flex-wrap: wrap;
  }

  .nf-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-md);
    padding: 0.7rem 1rem;
    text-decoration: none;
    font-weight: 600;
    transition: var(--transition-fast);
    border: 1px solid transparent;
  }

  .nf-btn-primary {
    background: var(--btn-primary-bg);
    color: var(--btn-primary-text);
  }

  .nf-btn-primary:hover {
    filter: brightness(1.05);
  }

  .nf-btn-ghost {
    background: var(--btn-secondary-bg);
    color: var(--btn-secondary-text);
    border-color: var(--border);
  }

  .nf-btn-ghost:hover {
    border-color: var(--border-bright);
  }
`;
