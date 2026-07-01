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
    border: 1px solid var(--glass-border);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
    border-radius: var(--radius-xl);
    background:
      radial-gradient(circle at 20% 20%, color-mix(in srgb, var(--secondary) 16%, transparent), transparent 40%),
      var(--bg-surface);
    box-shadow: var(--shadow-inner), var(--shadow-lg);
    padding: 3rem;
    text-align: center;
  }

  .nf-code {
    font-family: var(--font-mono);
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 800;
    letter-spacing: 0.08em;
    color: var(--secondary);
    margin-bottom: 0.5rem;
    text-shadow: 0 0 20px var(--secondary-glow);
  }

  .nf-title {
    font-size: clamp(1.5rem, 3.5vw, 2.5rem);
    color: var(--text-main);
    margin-bottom: 0.75rem;
  }

  .nf-text {
    color: var(--text-muted);
    max-width: 48ch;
    margin: 0 auto 2rem;
    line-height: 1.6;
  }

  .nf-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
  }

  .nf-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-md);
    padding: 0.8rem 1.5rem;
    text-decoration: none;
    font-weight: 600;
    transition: var(--transition-base);
    border: 1px solid transparent;
  }

  .nf-btn-primary {
    background: var(--secondary);
    color: white;
    box-shadow: 0 4px 12px var(--secondary-glow);
  }

  .nf-btn-primary:hover {
    filter: brightness(1.1);
    transform: translateY(-1px);
    box-shadow: 0 6px 18px var(--secondary-glow);
  }

  .nf-btn-ghost {
    background: var(--bg-card);
    color: var(--text-muted);
    border-color: var(--glass-border);
    backdrop-filter: var(--glass-blur);
  }

  .nf-btn-ghost:hover {
    border-color: var(--border-bright);
    color: var(--text-main);
    background: var(--bg-surface);
  }
`;
