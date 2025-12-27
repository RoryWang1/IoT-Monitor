import React from 'react';

interface DeviceIconProps {
  size?: number;
  color?: string;
}

const DeviceIcon: React.FC<DeviceIconProps> = ({ size = 16, color = '#E5E7EB' }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect
        x="3"
        y="4"
        width="18"
        height="14"
        rx="2"
        stroke={color}
        strokeWidth="2"
        fill="none"
      />
      <rect
        x="6"
        y="7"
        width="12"
        height="8"
        rx="1"
        fill={color}
        opacity="0.3"
      />
      <circle
        cx="12"
        cy="11"
        r="2"
        fill={color}
      />
      <rect
        x="10"
        y="19"
        width="4"
        height="1"
        fill={color}
      />
    </svg>
  );
};

export default DeviceIcon; 