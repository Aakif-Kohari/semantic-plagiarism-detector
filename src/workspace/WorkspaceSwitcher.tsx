'use client';

import React, { useState } from 'react';
import { Building2, ChevronDown } from 'lucide-react';

export default function WorkspaceSwitcher() {
  const [currentWorkspace, setCurrentWorkspace] = useState('Default Organization');
  const [isOpen, setIsOpen] = useState(false);

  const workspaces = ['Default Organization', 'Computer Science Dept', 'Engineering School'];

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-neutral-100 dark:bg-neutral-800 rounded-xl text-xs font-bold transition"
      >
        <Building2 className="w-4 h-4 text-amber-500" />
        <span>{currentWorkspace}</span>
        <ChevronDown className="w-3.5 h-3.5 text-neutral-400" />
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 w-48 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl shadow-lg p-1.5 z-50 text-xs">
          {workspaces.map((ws) => (
            <button
              key={ws}
              onClick={() => {
                setCurrentWorkspace(ws);
                setIsOpen(false);
              }}
              className="w-full text-left px-3 py-2 rounded-xl hover:bg-neutral-100 dark:hover:bg-neutral-800 font-medium transition"
            >
              {ws}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
