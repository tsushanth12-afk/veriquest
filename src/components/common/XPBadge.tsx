import React from 'react';

interface XPBadgeProps {
  xp: number;
}

export const XPBadge: React.FC<XPBadgeProps> = ({ xp }) => {
  return (
    <span
      className="neu-badge"
      style={{
        color: 'var(--accent)',
        backgroundColor: 'var(--accent-subtle)',
        borderColor: 'rgba(201, 111, 74, 0.25)',
      }}
    >
      +{xp} XP
    </span>
  );
};
