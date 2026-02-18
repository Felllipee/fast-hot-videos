
export interface Video {
  id: string;
  title: string;
  thumbnail: string;
  videoUrl: string;
  category: string;
  duration: string;
  views: string;
  rating: number;
  isShort?: boolean;
  isTrending?: boolean;
}

export type Category = 'All' | 'Amateur' | 'Professional' | 'Latina' | 'Brazillian' | 'Pov' | 'Hardcore' | 'Softcore';

export interface User {
  email: string;
  name: string;
  favorites: string[];
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
