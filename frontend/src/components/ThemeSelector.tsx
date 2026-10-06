import { useTheme, type Theme } from '../ThemeContext';

const themes: { id: Theme; label: string; icon: string }[] = [
  { id: 'light', label: 'Light', icon: '☀️' },
  { id: 'dark', label: 'Dark', icon: '🌙' },
  { id: 'eco', label: 'Eco', icon: '🌿' },
];

export function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="theme-selector" aria-label="Choose dashboard theme">
      {themes.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`theme-selector__button ${
            theme === item.id ? 'is-active' : ''
          }`}
          onClick={() => setTheme(item.id)}
          aria-pressed={theme === item.id}
          title={`${item.label} theme`}
        >
          <span aria-hidden="true">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
}