import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function Button({
  children,
  variant = 'default',
  size = 'default',
  className,
  ...props
}) {
  const variants = {
    default: 'bg-primary-500 text-white hover:bg-primary-600',
    outline: 'border border-neutral-300 dark:border-neutral-600 bg-transparent text-neutral-900 dark:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-700',
    ghost: 'bg-transparent text-neutral-900 dark:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-700',
    danger: 'bg-red-500 text-white hover:bg-red-600',
    secondary: 'bg-neutral-200 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 hover:bg-neutral-300 dark:hover:bg-neutral-600',
  }

  const sizes = {
    default: 'px-4 py-2',
    sm: 'px-3 py-1.5 text-sm',
    lg: 'px-6 py-3',
    icon: 'p-2',
  }

  return (
    <button
      className={twMerge(
        clsx(
          'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none',
          variants[variant],
          sizes[size],
          className
        )
      )}
      {...props}
    >
      {children}
    </button>
  )
}
