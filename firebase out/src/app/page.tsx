'use client';

import React, { useState, useEffect } from 'react';
import { SplashScreen } from '@/components/SplashScreen';
import { TemporalTopBar } from '@/components/TemporalTopBar';
import { TopicNavigator } from '@/components/TopicNavigator';
import { NewsCard } from '@/components/NewsCard';
import { NewsDetail } from '@/components/NewsDetail';
import { NewsArticle } from '@/app/data/news-data';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2 } from 'lucide-react';

export default function Home() {
  const [showSplash, setShowSplash] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('全部');
  const [activeArticle, setActiveArticle] = useState<NewsArticle | null>(null);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        const response = await fetch('https://raw.githubusercontent.com/EveLee-Teuk/yesterdays-headlines-data/main/today_news.json');
        if (!response.ok) {
          throw new Error('无法连接至新闻服务器');
        }
        const data = await response.json();
        
        // Map fetched fields to our internal NewsArticle structure
        const mappedNews: NewsArticle[] = data.map((item: any, index: number) => {
          // Subtitle usually looks like "2017年 北京"
          const subtitleParts = (item.subtitle || '').split(' ');
          const timestamp = subtitleParts[0] || '';
          const location = subtitleParts.slice(1).join(' ') || '';
          
          return {
            id: String(index),
            originalHeadline: item.title,
            articleBody: item.summary,
            category: item.category as any,
            location: location,
            timestamp: timestamp,
            imageId: item.category === '科技' ? 'tech-1' : (item.category === '民生' ? 'livelihood-1' : 'society-1')
          };
        });
        
        setNews(mappedNews);
        setError(null);
      } catch (err: any) {
        console.error('Fetch error:', err);
        setError(err.message || '加载新闻失败');
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, []);

  const filteredNews = selectedCategory === '全部' 
    ? news 
    : news.filter(article => article.category === selectedCategory);

  if (showSplash) {
    return <SplashScreen onComplete={() => setShowSplash(false)} />;
  }

  if (activeArticle) {
    return <NewsDetail article={activeArticle} onBack={() => setActiveArticle(null)} />;
  }

  return (
    <main className="flex flex-col h-screen animate-fade-in">
      <TemporalTopBar />
      
      <TopicNavigator 
        selected={selectedCategory} 
        onSelect={setSelectedCategory} 
      />

      <ScrollArea className="flex-1">
        <div className="pb-10">
          {loading ? (
            <div className="flex flex-col items-center justify-center p-20 text-white/40">
              <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
              <p className="text-sm font-bold tracking-widest uppercase">采编中...</p>
            </div>
          ) : error ? (
            <div className="p-10 text-center text-primary/60 italic font-headline text-lg">
              {error}
              <button 
                onClick={() => window.location.reload()}
                className="block mx-auto mt-4 text-xs font-bold uppercase tracking-widest text-white/40 hover:text-white"
              >
                尝试重新连接
              </button>
            </div>
          ) : filteredNews.length > 0 ? (
            filteredNews.map((article, idx) => (
              <div 
                key={article.id} 
                className="animate-fade-in"
                style={{ animationDelay: `${idx * 100}ms` }}
              >
                <NewsCard 
                  article={article} 
                  onClick={() => setActiveArticle(article)}
                />
              </div>
            ))
          ) : (
            <div className="p-10 text-center text-white/30 italic font-headline text-lg">
              今日无此类报道
            </div>
          )}
          
          {!loading && !error && (
            <div className="mt-12 mb-8 text-center">
              <div className="h-px bg-white/5 w-1/4 mx-auto mb-4" />
              <p className="text-[10px] uppercase tracking-[0.2em] text-white/20 font-bold">
                本刊完
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
      
      <footer className="bg-obsidian border-t border-white/5 p-4 flex justify-around items-center">
        <div className="w-1 h-1 rounded-full bg-primary" />
        <div className="w-1 h-1 rounded-full bg-white/20" />
        <div className="w-1 h-1 rounded-full bg-white/20" />
      </footer>
    </main>
  );
}
