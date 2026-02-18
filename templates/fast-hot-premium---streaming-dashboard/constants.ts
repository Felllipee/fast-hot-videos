
import { Video, Category } from './types';

export const CATEGORIES: Category[] = [
  'All',
  // Fix: changed 'Amador' to 'Amateur' to match Category type in types.ts
  'Amateur',
  // Fix: changed 'Profissional' to 'Professional' to match Category type in types.ts
  'Professional',
  'Latina',
  // Fix: changed 'Brasileira' to 'Brazillian' to match Category type in types.ts
  'Brazillian',
  // Fix: changed 'POV' to 'Pov' to match Category type in types.ts
  'Pov',
  'Hardcore',
  'Softcore'
];

export const HERO_VIDEOS = [
  'https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4'
];

export const MOCK_VIDEOS: Video[] = [
  {
    id: '1',
    title: 'Noite de Verão em São Paulo',
    thumbnail: 'https://picsum.photos/seed/v1/800/450',
    videoUrl: 'https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
    // Fix: Updated category value to match the new Category definition
    category: 'Amateur',
    duration: '12:45',
    views: '1.2M',
    rating: 4.8,
    isTrending: true
  },
  {
    id: '2',
    title: 'Produção Exclusiva Fast Hot',
    thumbnail: 'https://picsum.photos/seed/v2/800/450',
    videoUrl: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
    // Fix: Updated category value to match the new Category definition
    category: 'Professional',
    duration: '22:10',
    views: '850k',
    rating: 4.9,
    isTrending: true
  },
  {
    id: '3',
    title: 'POV: Encontro Inesperado',
    thumbnail: 'https://picsum.photos/seed/v3/800/450',
    videoUrl: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    // Fix: Updated category value to match the new Category definition
    category: 'Pov',
    duration: '08:15',
    views: '2.5M',
    rating: 4.5
  },
  {
    id: '4',
    title: 'Short: Dança Sensual',
    thumbnail: 'https://picsum.photos/seed/s1/400/700',
    videoUrl: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
    category: 'Softcore',
    duration: '00:58',
    views: '4.1M',
    rating: 4.7,
    isShort: true
  },
  {
    id: '5',
    title: 'Short: Close-up Intenso',
    thumbnail: 'https://picsum.photos/seed/s2/400/700',
    videoUrl: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4',
    category: 'Hardcore',
    duration: '00:45',
    views: '3.2M',
    rating: 4.6,
    isShort: true
  },
  {
    id: '6',
    title: 'Latina Hot Beats',
    thumbnail: 'https://picsum.photos/seed/v4/800/450',
    videoUrl: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4',
    category: 'Latina',
    duration: '15:30',
    views: '900k',
    rating: 4.4
  }
];
