interface AvatarProps {
  name: string;
  size?: number;
  photoUrl?: string;
  className?: string;
}

function nameHash(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash += name.charCodeAt(i);
  }
  return hash;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0]!.charAt(0).toUpperCase();
  return (parts[0]!.charAt(0) + parts[parts.length - 1]!.charAt(0)).toUpperCase();
}

export default function Avatar({
  name,
  size = 48,
  photoUrl,
  className = "",
}: AvatarProps) {
  const hash = nameHash(name);
  const bgColor = `hsl(${hash % 360}, 50%, 40%)`;

  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={name}
        className={className}
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          objectFit: "cover",
        }}
      />
    );
  }

  return (
    <div
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        backgroundColor: bgColor,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#fff",
        fontSize: size * 0.4,
        fontWeight: 600,
        userSelect: "none",
      }}
      aria-label={name}
    >
      {initials(name)}
    </div>
  );
}
