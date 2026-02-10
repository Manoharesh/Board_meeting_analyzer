import React from 'react';
import '../styles/AppButton.css';

const AppButton = React.forwardRef(function AppButton(
  {
    children,
    className = '',
    innerClassName = '',
    type = 'button',
    ...props
  },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      className={`button ${className}`.trim()}
      {...props}
    >
      <span className="blob1" aria-hidden="true" />
      <span className={`inner ${innerClassName}`.trim()}>{children}</span>
    </button>
  );
});

export default AppButton;
