'use client';

import React, { useRef, useState, useEffect } from 'react';
import Image from 'next/image';
import { NewsArticle } from '@/app/data/news-data';
import { PlaceHolderImages } from '@/lib/placeholder-images';
import { ChevronLeft, MapPin, Clock, Share2, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface NewsDetailProps {
  article: NewsArticle;
  onBack: () => void;
}

export function NewsDetail({ article, onBack }: NewsDetailProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const posterRef = useRef<HTMLDivElement>(null);
  const [currentDate, setCurrentDate] = useState('');

  useEffect(() => {
    const now = new Date();
    const formatted = new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(now);
    setCurrentDate(formatted);
  }, []);

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
  const imageUrl = image?.imageUrl || `https://picsum.photos/seed/${article.id}/800/600`;
  const imageDescription = image?.description || "新闻详情插图";
  const imageHint = image?.imageHint || "news event";

  const handleGeneratePoster = async () => {
    if (!posterRef.current || isGenerating) return;

    try {
      setIsGenerating(true);
      
      // Dynamic import to avoid SSR and module resolution issues during startup
      const html2canvas = (await import('html2canvas')).default;

      // Small delay to ensure any potential state changes are rendered
      await new Promise(resolve => setTimeout(resolve, 150));

      const canvas = await html2canvas(posterRef.current, {
        useCORS: true,
        backgroundColor: '#171212',
        scale: 2, // Higher quality for the poster
        logging: false,
      });

      const dataUrl = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.download = `昨日头条-日签-${article.id}.png`;
      link.href = dataUrl;
      link.click();
    } catch (error) {
      console.error('Failed to generate poster:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col h-[100dvh] bg-obsidian animate-fade-in relative overflow-hidden">
      {/* Hidden Poster Layout for Capture */}
      <div className="fixed left-[-9999px] top-0 pointer-events-none">
        <div 
          ref={posterRef}
          className="w-[375px] bg-[#171212] p-8 flex flex-col relative overflow-hidden"
          style={{ minHeight: '667px' }}
        >
          {/* Decorative Border */}
          <div className="absolute inset-4 border border-primary/20 pointer-events-none" />
          
          {/* Header */}
          <div className="flex flex-col mb-8 relative z-10">
            <h1 className="font-headline text-3xl font-bold text-primary leading-none tracking-tighter italic uppercase">
              昨日
            </h1>
            <h2 className="font-headline text-4xl font-bold text-white leading-none tracking-tighter uppercase mb-2">
              头条
            </h2>
            <div className="h-0.5 w-full bg-primary/30 rounded-full mb-4" />
            <div className="flex justify-between items-center text-[10px] text-white/40 uppercase tracking-widest font-bold">
              <span>{currentDate}</span>
              <span className="text-primary">第十二卷</span>
            </div>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 flex flex-col relative z-10">
            <div className="relative aspect-[4/3] w-full mb-6 rounded-sm overflow-hidden border border-white/5">
              {/* Note: Standard img used for better html2canvas compatibility */}
              <img 
                src={imageUrl} 
                alt={imageDescription}
                className="w-full h-full object-cover grayscale"
                crossOrigin="anonymous"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-obsidian/60 to-transparent" />
            </div>

            <Badge variant="outline" className="w-fit mb-4 bg-primary/10 text-primary border-primary/20 font-bold text-[10px] uppercase tracking-wider">
              {article.category}
            </Badge>

            <h3 className="font-headline text-2xl font-bold leading-tight text-white mb-6">
              {article.originalHeadline}
            </h3>

            <div className="flex gap-4 text-[10px] text-white/40 font-bold mb-6">
              <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{article.location}</span>
              <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{article.timestamp}</span>
            </div>

            <p className="text-white/60 text-xs leading-relaxed line-clamp-6 italic border-l-2 border-primary/20 pl-4">
              {article.articleBody}
            </p>
          </div>

          {/* Footer Branding */}
          <div className="mt-8 flex flex-col items-center gap-2 relative z-10">
            <div className="h-px w-12 bg-white/10" />
            <p className="text-[8px] text-white/20 uppercase tracking-[0.3em] font-bold">
              深度报道 · 精致阅读
            </p>
          </div>
        </div>
      </div>

      {/* Top Navigation */}
      <div className="absolute top-0 left-0 right-0 z-50 p-4 pointer-events-none">
        <button 
          onClick={onBack}
          className="p-2 rounded-full bg-obsidian/60 backdrop-blur-md text-white hover:bg-obsidian/80 transition-colors flex items-center gap-1 text-sm font-bold shadow-lg pointer-events-auto"
        >
          <ChevronLeft className="w-5 h-5" />
          返回
        </button>
      </div>

      {/* Main Content Wrapper */}
      <div className="flex-1 overflow-y-auto scroll-smooth no-scrollbar">
        <div className="relative w-full aspect-[4/3] bg-white/5">
          <Image
            src={imageUrl}
            alt={imageDescription}
            fill
            className="object-cover grayscale hover:grayscale-0 transition-all duration-700"
            data-ai-hint={imageHint}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-transparent to-transparent" />
        </div>

        <div className="px-6 py-8 -mt-12 relative z-10">
          <div className="flex items-center gap-3 mb-6">
            <Badge 
              variant="outline" 
              className="bg-primary/20 text-primary border-primary/30 font-bold text-xs uppercase tracking-widest px-3 py-1"
            >
              {article.category}
            </Badge>
          </div>

          <h1 className="font-headline text-3xl font-bold leading-tight text-white mb-6">
            {article.originalHeadline}
          </h1>

          <div className="flex flex-wrap gap-6 text-sm text-white/40 mb-10 border-y border-white/5 py-4">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-primary" />
              <span className="font-bold">{article.location}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" />
              <span className="font-bold">{article.timestamp}</span>
            </div>
          </div>

          <article className="prose prose-invert max-w-none">
            <p className="text-white/80 text-lg leading-relaxed font-body first-letter:text-4xl first-letter:font-bold first-letter:text-primary first-letter:mr-3 first-letter:float-left mb-8">
              {article.articleBody}
            </p>
          </article>

          {/* Spacer block to ensure scrolling clear of FAB */}
          <div className="h-40 w-full shrink-0" aria-hidden="true"></div>

          <div className="mt-8 text-center pb-8">
            <div className="h-px bg-white/5 w-1/4 mx-auto mb-4" />
            <p className="text-[10px] uppercase tracking-[0.2em] text-white/20 font-bold italic">
              — 昨日头条 深度报道 —
            </p>
          </div>
        </div>
      </div>

      {/* Floating Action Button Container */}
      <div className="absolute bottom-8 left-0 right-0 px-6 z-50 pointer-events-none">
        <div className="max-w-md mx-auto pointer-events-auto">
          <Button 
            onClick={handleGeneratePoster}
            disabled={isGenerating}
            className="w-full h-14 rounded-full bg-primary hover:bg-primary/90 text-white shadow-[0_10px_40px_-10px_rgba(242,38,38,0.5)] font-bold text-base tracking-widest gap-2 border-none transition-all"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                正在生成...
              </>
            ) : (
              <>
                <Share2 className="w-5 h-5" />
                生成日签
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}