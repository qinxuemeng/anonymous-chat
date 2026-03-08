export default function MatchCard({
  title,
  description,
  color,
  icon: Icon,
  onClick,
  disabled = false
}) {
  const handleClick = () => {
    if (!disabled && onClick) {
      onClick()
    }
  }

  return (
    <div
      onClick={handleClick}
      className={`rounded-2xl px-4 py-5 sm:p-6 min-h-[112px] sm:min-h-[176px] flex items-center sm:flex-col sm:items-center justify-start sm:justify-center text-white transition-transform ${
        disabled
          ? 'opacity-50 cursor-not-allowed'
          : 'cursor-pointer active:scale-[0.99] sm:hover:scale-[1.02] hover:opacity-95'
      } ${color}`}
    >
      <Icon className="w-9 h-9 sm:w-12 sm:h-12 shrink-0" />
      <div className="ml-3 sm:ml-0 sm:mt-3 text-left sm:text-center">
        <h3 className="text-2xl sm:text-xl font-bold leading-none">{title}</h3>
        {description && (
          <p className="text-sm opacity-90 mt-2">{description}</p>
        )}
      </div>
    </div>
  )
}
