import React from 'react';

interface ServerIconProps {
  size?: number;
  color?: string;
}

const ServerIcon: React.FC<ServerIconProps> = ({ size = 16, color = '#E5E7EB' }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect
        x="2"
        y="3"
        width="20"
        height="5"
        rx="2"
        stroke={color}
        strokeWidth="2"
        fill="none"
      />
      <rect
        x="2"
        y="10"
        width="20"
        height="5"
        rx="2"
        stroke={color}
        strokeWidth="2"
        fill="none"
      />
      <rect
        x="2"
        y="17"
        width="20"
        height="4"
        rx="2"
        stroke={color}
        strokeWidth="2"
        fill="none"
      />
      <circle cx="6" cy="5.5" r="1" fill={color} />
      <circle cx="6" cy="12.5" r="1" fill={color} />
      <circle cx="6" cy="19" r="1" fill={color} />
      <rect x="10" y="4.5" width="8" height="2" rx="1" fill={color} opacity="0.5" />
      <rect x="10" y="11.5" width="8" height="2" rx="1" fill={color} opacity="0.5" />
      <rect x="10" y="18" width="8" height="2" rx="1" fill={color} opacity="0.5" />
    </svg>
  );
};

export default ServerIcon; 