import React from 'react';
import { Difficulty } from '../../types/challenge';

interface DifficultyBadgeProps {
  difficulty: Difficulty;
  size?: 'sm' | 'md';
}

export const DifficultyBadge: React.FC<DifficultyBadgeProps> = ({ difficulty, size = 'sm' }) => {
  const getColors = () => {
    switch (difficulty) {
      case 'Easy':
        return {
          color: 'var(--status-sage)',
          bg: 'var(--status-sage-bg)',
          border: 'rgba(125, 135, 101, 0.3)',
        };
      case 'Medium':
        return {
          color: 'var(--status-warning)',
          bg: 'var(--status-warning-bg)',
          border: 'rgba(217, 130, 43, 0.3)',
        };
      case 'Hard':
        return {
          color: 'var(--status-error)',
          bg: 'var(--status-error-bg)',
          border: 'rgba(184, 74, 57, 0.3)',
        };
    }
  };

  const style = getColors();

  return (
    <span
      className="neu-badge"
      style={{
        color: style.color,
        backgroundColor: style.bg,
        borderColor: style.border,
        fontSize: size === 'sm' ? '10px' : '11px',
        padding: size === 'sm' ? '2px 6px' : '3px 8px',
      }}
    >
      {difficulty}
    </span>
  );
};
