import React from 'react';

interface DatabaseIconProps {
  size?: number;
  color?: string;
}

const DatabaseIcon: React.FC<DatabaseIconProps> = ({ size = 16, color = '#6B7280' }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <ellipse
        cx="12"
        cy="5"
        rx="9"
        ry="3"
        stroke={color}
        strokeWidth="2"
      />
      <path
        d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"
        stroke={color}
        strokeWidth="2"
      />
      <path
        d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"
        stroke={color}
        strokeWidth="2"
      />
    </svg>
  );
};

export default DatabaseIcon; 