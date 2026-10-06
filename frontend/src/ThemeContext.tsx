import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

export type Theme = 'light' | 'dark' | 'eco';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  hasSelectedTheme: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const STORAGE_KEY = 'campus-twin-theme';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const savedTheme = localStorage.getItem(STORAGE_KEY);

    if (
      savedTheme === 'light' ||
      savedTheme === 'dark' ||
      savedTheme === 'eco'
    ) {
      return savedTheme;
    }

    return 'light';
  });

  const [hasSelectedTheme, setHasSelectedTheme] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) !== null;
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem(STORAGE_KEY, newTheme);
    setHasSelectedTheme(true);
  };

  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme,
        hasSelectedTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);

  if (!context) {
    throw new Error('useTheme must be used inside ThemeProvider');
  }

  return context;
}