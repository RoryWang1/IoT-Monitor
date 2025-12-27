import React from 'react';

interface GatewayIconProps {
  size?: number;
  color?: string;
}

const GatewayIcon: React.FC<GatewayIconProps> = ({ size = 16, color = '#E5E7EB' }) => {
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
        r="9"
        stroke={color}
        strokeWidth="2"
        fill="none"
      />
      <circle
        cx="12"
        cy="12"
        r="5"
        stroke={color}
        strokeWidth="2"
        fill="none"
      />
      <circle
        cx="12"
        cy="12"
        r="2"
        fill={color}
      />
      <path
        d="M12 3v2M12 19v2M3 12h2M19 12h2"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M6.34 6.34l1.41 1.41M16.25 16.25l1.41 1.41M6.34 17.66l1.41-1.41M16.25 7.75l1.41-1.41"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
};

export default GatewayIcon; 