interface AvatarProps {
  name: string
  /** Falls back to the first letter of `name` when absent */
  src?: string | null
  size?: 'tiny' | 'small' | 'medium' | 'large'
}
export function Avatar({ name, src, size = 'medium' }: AvatarProps) {
  const classes = ['avatar', size !== 'medium' && `avatar--${size}`].filter(Boolean).join(' ')
  const letter = name.trim().charAt(0).toUpperCase() || '?'
  return (
    <div className={classes} aria-label={name}>
      {src ? <img src={src} alt={name} /> : letter}
    </div>
  )
}
