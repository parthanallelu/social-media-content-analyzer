import clsx from 'clsx';

/**
 * Reusable Button component with three variants: primary, secondary, ghost.
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  children,
  loading = false,
  disabled = false,
  className = '',
  ...props
}) {
  const variantClass = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    ghost: 'btn-ghost',
  }[variant];

  const sizeClass = {
    sm: 'text-xs px-3 py-1.5',
    md: '',
    lg: 'text-base px-6 py-3',
  }[size];

  return (
    <button
      className={clsx(variantClass, sizeClass, className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin h-4 w-4 flex-shrink-0"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
