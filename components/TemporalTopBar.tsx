'use client';

import React, { useEffect, useState } from 'react';

export function TemporalTopBar() {
  const [currentDate, setCurrentDate] = useState<string>('');

  useEffect(() => {
    const now = new Date();
    const formatted = new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long',
    }).format(now);
    setCurrentDate(formatted);
  }, []);

  return (
    <header className="sticky top-0 z-30 bg-obsidian/95 backdrop-blur-md px-4 pt-8 pb-4 border-b border-white/5">
      <div className="flex flex-col">
        <h1 className="font-headline text-3xl font-bold text-primary leading-none tracking-tighter uppercase italic">
          昨日
        </h1>
        <div className="flex items-center justify-between">
          <h2 className="font-headline text-4xl font-bold text-white leading-none tracking-tighter uppercase">
            头条
          </h2>
          <div className="h-0.5 flex-1 mx-4 bg-primary/30 rounded-full" />
        </div>
        <div className="mt-4 flex items-center justify-between text-[11px] uppercase tracking-widest font-bold text-white/40">
          <span>{currentDate}</span>
          <span className="text-primary">第十二卷</span>
        </div>
      </div>
    </header>
  );
}