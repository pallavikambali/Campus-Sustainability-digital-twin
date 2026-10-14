import { useTheme, type Theme } from '../ThemeContext';

const themes: { id: Theme; label: string }[] = [
  { id: 'light', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'eco', label: 'Eco' },
];

export function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="theme-selector" role="group" aria-label="Choose dashboard theme">
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
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
}