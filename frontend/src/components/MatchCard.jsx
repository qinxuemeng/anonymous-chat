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
      className={`rounded-2xl p-6 flex flex-col items-center justify-center text-white transition-transform ${
        disabled
          ? 'opacity-50 cursor-not-allowed'
          : 'cursor-pointer hover:scale-105 hover:opacity-90'
      } ${color}`}
    >
      <Icon className="w-12 h-12 mb-3" />
      <h3 className="text-xl font-bold text-center">{title}</h3>
      {description && (
        <p className="text-sm opacity-90 text-center mt-1">{description}</p>
      )}
    </div>
  )
}
