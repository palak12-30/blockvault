const RISK_STYLES = {
  low: { label: "Low risk", className: "fraud-badge--low" },
  medium: { label: "Medium risk", className: "fraud-badge--medium" },
  high: { label: "High risk", className: "fraud-badge--high" },
};

export default function FraudBadge({ assessment }) {
  if (!assessment) return null;

  if (assessment.error) {
    return (
      <div className="fraud-badge fraud-badge--unavailable">
        Fraud check unavailable — proceeding without a risk score.
      </div>
    );
  }

  const style = RISK_STYLES[assessment.risk_level] || RISK_STYLES.low;
  const percent = Math.round(assessment.fraud_probability * 100);

  return (
    <div className={`fraud-badge ${style.className}`}>
      <div className="fraud-badge__row">
        <span className="fraud-badge__label">{style.label}</span>
        <span className="fraud-badge__percent">{percent}% fraud probability</span>
      </div>
      {assessment.risk_level === "high" && (
        <p className="fraud-badge__warning">
          This document scored as high risk based on its size, metadata, and
          structure. You can still register it — this is informational, not a block.
        </p>
      )}
    </div>
  );
}
