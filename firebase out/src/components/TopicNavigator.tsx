'use client';

import React from 'react';
import { cn } from '@/lib/utils';

const CATEGORIES = ['全部', '民生', '科技', '社会'] as const;

interface TopicNavigatorProps {
  selected: string;
  onSelect: (category: string) => void;
}

export function TopicNavigator({ selected, onSelect }: TopicNavigatorProps) {
  return (
    <nav className="sticky top-[145px] z-20 bg-obsidian/90 backdrop-blur-sm py-4">
      <div className="flex overflow-x-auto no-scrollbar gap-2 px-4 scroll-smooth">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => onSelect(cat)}
            className={cn(
              "px-5 py-2 rounded-full text-xs font-bold uppercase tracking-widest whitespace-nowrap transition-all duration-300",
              selected === cat 
                ? "bg-primary text-white shadow-lg shadow-primary/20" 
                : "bg-white/5 text-white/50 hover:bg-white/10"
            )}
          >
            {cat}
          </button>
        ))}
      </div>
    </nav>
  );
}