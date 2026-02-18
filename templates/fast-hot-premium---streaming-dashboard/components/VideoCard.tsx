
import React, { useState } from 'react';
import { Video } from '../types';

interface VideoCardProps {
  video: Video;
  isFavorite: boolean;
  onToggleFavorite: (e: React.MouseEvent, id: string) => void;
  onClick: (video: Video) => void;
}

export const VideoCard: React.FC<VideoCardProps> = ({ video, isFavorite, onToggleFavorite, onClick }) => {
  return (
    <div 
      className={`group relative overflow-hidden rounded-xl bg-gray-900 border border-gray-800 transition-all duration-300 hover:scale-105 hover:border-red-600/50 hover:shadow-[0_0_20px_rgba(220,38,38,0.2)] cursor-pointer ${video.isShort ? 'aspect-[9/16]' : 'aspect-video'}`}
      onClick={() => onClick(video)}
    >
      <img 
        src={video.thumbnail} 
        alt={video.title}
        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110 opacity-70 group-hover:opacity-100"
      />
      
      {/* Botão Favoritar */}
      <button 
        onClick={(e) => onToggleFavorite(e, video.id)}
        className={`absolute top-2 right-2 z-20 p-2 rounded-full backdrop-blur-md transition-all ${isFavorite ? 'bg-red-600 text-white' : 'bg-black/40 text-gray-300 hover:text-white hover:bg-black/60'}`}
      >
        <svg className={`w-4 h-4 ${isFavorite ? 'fill-current' : 'fill-none'}`} stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
        </svg>
      </button>

      {/* Play Overlay */}
      <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="bg-red-600 rounded-full p-3 transform scale-75 group-hover:scale-100 transition-transform">
          <svg className="w-8 h-8 text-white fill-current" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>

      {/* Info Badge */}
      <div className="absolute top-2 left-2 flex gap-1">
        {video.isTrending && (
          <span className="bg-red-600 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider animate-pulse">
            Em Alta
          </span>
        )}
        <span className="bg-black/60 backdrop-blur-md text-white text-[10px] px-2 py-0.5 rounded">
          {video.duration}
        </span>
      </div>

      {/* Title Gradient */}
      <div className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black via-black/60 to-transparent">
        <h3 className="text-sm font-semibold text-white truncate group-hover:text-red-500 transition-colors">
          {video.title}
        </h3>
        <div className="flex justify-between items-center mt-1">
          <span className="text-[10px] text-gray-400 font-medium">{video.category}</span>
          <span className="text-[10px] text-gray-400">{video.views} visualizações</span>
        </div>
      </div>
    </div>
  );
};
