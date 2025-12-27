import React from 'react';

interface NetworkIconProps {
  size?: number;
  color?: string;
}

const NetworkIcon: React.FC<NetworkIconProps> = ({ size = 16, color = '#6B7280' }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="12"
        cy="12"
        r="3"
        stroke={color}
        strokeWidth="2"
      />
      <circle
        cx="12"
        cy="5"
        r="2"
        stroke={color}
        strokeWidth="2"
      />
      <circle
        cx="5"
        cy="19"
        r="2"
        stroke={color}
        strokeWidth="2"
      />
      <circle
        cx="19"
        cy="19"
        r="2"
        stroke={color}
        strokeWidth="2"
      />
      <path
        d="M12 9v2M7 17l3-3M17 17l-3-3"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export default NetworkIcon; 