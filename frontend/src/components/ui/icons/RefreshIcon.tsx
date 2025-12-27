import React from 'react';

interface RefreshIconProps {
  size?: number;
  color?: string;
}

const RefreshIcon: React.FC<RefreshIconProps> = ({ size = 16, color = '#6B7280' }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9M20 20v-5h-.582m-15.356-2A8.001 8.001 0 0019.418 15"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export default RefreshIcon; 