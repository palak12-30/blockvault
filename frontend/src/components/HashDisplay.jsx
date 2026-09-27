export default function HashDisplay({ label, value }) {
  return (
    <div className="hash-display">
      <span className="hash-display__label">{label}</span>
      <code className="hash-display__value">{value}</code>
    </div>
  );
}
