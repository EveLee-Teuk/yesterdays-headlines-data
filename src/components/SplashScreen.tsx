'use client';

import React, { useEffect, useState } from 'react';
import { Newspaper } from 'lucide-react';

export function SplashScreen({ onComplete }: { onComplete: () => void }) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onComplete, 500); // Allow fade animation
    }, 2000);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className={`fixed inset-0 z-[100] flex items-center justify-center bg-primary transition-opacity duration-500 ${isVisible ? 'opacity-100' : 'opacity-0'}`}>
      <div className="text-center animate-pulse">
        <div className="inline-flex items-center justify-center p-6 rounded-3xl bg-white/10 backdrop-blur-md mb-6 shadow-2xl">
          <Newspaper className="w-16 h-16 text-white" strokeWidth={1.5} />
        </div>
        <h1 className="font-headline text-5xl font-bold text-white tracking-tighter uppercase leading-none italic mb-1">
          昨日
        </h1>
        <h2 className="font-headline text-6xl font-bold text-white tracking-tighter uppercase leading-none">
          头条
        </h2>
        <div className="mt-8 flex justify-center gap-1">
          <div className="w-2 h-2 rounded-full bg-white/40" />
          <div className="w-2 h-2 rounded-full bg-white/60" />
          <div className="w-2 h-2 rounded-full bg-white" />
        </div>
      </div>
    </div>
  );
}