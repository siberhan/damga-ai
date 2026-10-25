import { Link } from 'react-router-dom';

interface RoleGuideProps {
  step: number;
  role: string;
  steps: string[];
  next?: { label: string; to: string };
}

// Short "who are you, what to do here, where next" box at the top of each screen
export function RoleGuide({ step, role, steps, next }: RoleGuideProps) {
  return (
    <div className="role-guide">
      <div className="role-guide-head">
        <span className="role-guide-step">Step {step} of 3</span>
        <span className="role-guide-role">{role}</span>
      </div>
      <ol className="role-guide-steps">
        {steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      {next && (
        <Link to={next.to} className="btn btn-primary role-guide-next">
          {next.label} →
        </Link>
      )}
    </div>
  );
}
