'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { Badge } from '@/components/ui/badge';
import { PlaceHolderImages } from '@/lib/placeholder-images';
import { NewsArticle } from '@/app/data/news-data';
import { generateCatchyHeadline } from '@/ai/flows/generate-catchy-headline-flow';
import { Sparkles, MapPin, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NewsCardProps {
  article: NewsArticle;
  onClick?: () => void;
}

export function NewsCard({ article, onClick }: NewsCardProps) {
  const [headline, setHeadline] = useState(article.originalHeadline);
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Dynamic image selection based on category fallback
  const getCategoryImage = () => {
    if (article.imageId) {
      const img = PlaceHolderImages.find((i) => i.id === article.imageId);
      if (img) return img;
    }
    
    switch (article.category) {
      case '科技':
        return PlaceHolderImages.find(i => i.id.startsWith('tech')) || PlaceHolderImages[0];
      case '民生':
        return PlaceHolderImages.find(i => i.id.startsWith('live')) || PlaceHolderImages[0];
      case '社会':
        return PlaceHolderImages.find(i => i.id.startsWith('soc')) || PlaceHolderImages[0];
      default:
        return PlaceHolderImages[0];
    }
  };

  const image = getCategoryImage();
  const imageUrl = image?.imageUrl || `https://picsum.photos/seed/${article.id}/400/400`;
  const imageDescription = image?.description || "新闻报道插图";
  const imageHint = image?.imageHint || "journalism";

  const handleGenerate = (e: React.MouseEvent) => {
    e.stopPropagation(); 
    setIsGenerating(true);
    generateCatchyHeadline({ articleBody: article.articleBody })
      .then((result) => {
        if (result?.headline) {
          setHeadline(result.headline);
        }
      })
      .finally(() => {
        setIsGenerating(false);
      });
  };

  return (
    <div 
      onClick={onClick}
      className="flex gap-4 p-4 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors group cursor-pointer"
    >
      <div className="relative w-28 h-28 shrink-0 overflow-hidden rounded-lg bg-white/5">
        <Image
          src={imageUrl}
          alt={imageDescription}
          width={112}
          height={112}
          className="object-cover w-full h-full grayscale group-hover:grayscale-0 transition-all duration-500"
          data-ai-hint={imageHint}
        />
      </div>
      
      <div className="flex flex-col flex-1 justify-between py-1">
        <div>
          <div className="flex items-center justify-between mb-1">
            <Badge 
              variant="outline" 
              className="bg-primary/10 text-primary border-primary/20 font-bold text-[10px] uppercase tracking-wider"
            >
              {article.category}
            </Badge>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className={cn(
                "p-1.5 rounded-full hover:bg-white/10 transition-all disabled:opacity-50",
                isGenerating && "animate-spin"
              )}
              title="生成吸睛标题"
            >
              <Sparkles className="w-3 h-3 text-primary" />
            </button>
          </div>
          
          <h3 className={cn(
            "font-headline text-lg font-bold leading-tight text-white mb-2 line-clamp-2",
            isGenerating && "opacity-50"
          )}>
            {headline}
          </h3>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/40">
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {article.location}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {article.timestamp}
          </span>
        </div>
      </div>
    </div>
  );
}
