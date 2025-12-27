import React from 'react';

interface CheckIconProps {
  size?: number;
  color?: string;
}

const CheckIcon: React.FC<CheckIconProps> = ({ size = 16, color = '#10B981' }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M20 6L9 17l-5-5"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export default CheckIcon; 