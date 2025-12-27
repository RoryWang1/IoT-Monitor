import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
  padding?: 'sm' | 'md' | 'lg' | 'xl';
  style?: React.CSSProperties;
}

const Card: React.FC<CardProps> = ({ 
  children, 
  className = '', 
  onClick, 
  hover = false,
  padding = 'md',
  style
}) => {
  const paddingMap = {
    sm: 'var(--card-padding-sm)',
    md: 'var(--card-padding-md)',
    lg: 'var(--card-padding-lg)',
    xl: 'var(--card-padding-xl)'
  };

  const baseStyle: React.CSSProperties = {
    backgroundColor: 'var(--color-bg-secondary)',
    border: '1px solid var(--color-border-primary)',
    borderRadius: 'var(--radius-lg)',
    padding: paddingMap[padding],
    transition: 'all 0.3s ease',
    boxShadow: 'var(--shadow-md)',
    width: '100%',
    position: 'relative',
    overflow: 'hidden',
    ...style
  };

  const hoverStyle: React.CSSProperties = {
    backgroundColor: 'var(--color-bg-secondary)',
    border: '1px solid var(--color-accent-blue)',
    borderRadius: 'var(--radius-lg)',
    padding: paddingMap[padding],
    transition: 'all 0.3s ease',
    transform: 'translateY(-2px)',
    boxShadow: 'var(--shadow-lg)',
    cursor: onClick ? 'pointer' : 'default',
    width: '100%',
    position: 'relative',
    overflow: 'hidden',
    ...style
  };

  const [isHovered, setIsHovered] = React.useState(false);

  return (
    <div
      className={`${className} ${hover && isHovered ? 'animate-fadeIn' : ''}`}
      style={hover && isHovered ? hoverStyle : baseStyle}
      onClick={onClick}
      onMouseEnter={() => hover && setIsHovered(true)}
      onMouseLeave={() => hover && setIsHovered(false)}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
    >
      {children}
    </div>
  );
};

export default Card; 