import React from 'react';
import { 
  Cpu, Database, Network, Boxes, Binary, FileCode2, 
  Terminal, LineChart, Brain, CheckCircle2, BookOpen, 
  Layers, Play, Sparkles, ArrowRight 
} from 'lucide-react';
import { MCQBroadTopic } from '../../types';
import { getTopicColorClasses } from '../../utils/mcqTopics';

const ICON_MAP: Record<string, React.ElementType> = {
  Cpu,
  Database,
  Network,
  Boxes,
  Binary,
  FileCode2,
  Terminal,
  LineChart,
  Brain
};

interface MCQTopicCardProps {
  topic: MCQBroadTopic;
  isSelected: boolean;
  onSelect: (topicId: string) => void;
  onStartQuiz?: (topicId: string) => void;
}

export const MCQTopicCard: React.FC<MCQTopicCardProps> = ({
  topic,
  isSelected,
  onSelect,
  onStartQuiz
}) => {
  const IconComponent = ICON_MAP[topic.icon] || BookOpen;
  const colors = getTopicColorClasses(topic.color);

  const solved = topic.solved_count || 0;
  const progressPct = topic.total_questions > 0 ? Math.round((solved / topic.total_questions) * 100) : 0;

  return (
    <div
      onClick={() => onSelect(topic.id)}
      className={`group relative rounded-xl p-4 transition-all duration-200 cursor-pointer border text-left flex flex-col justify-between ${
        isSelected
          ? 'bg-surface border-accent shadow-sm ring-1 ring-accent'
          : 'bg-surface hover:bg-surface-hover border-border hover:border-border/80 hover:shadow-xs'
      }`}
    >
      <div>
        {/* Top Header: Icon & Short Tag */}
        <div className="flex items-center justify-between gap-2 mb-2.5">
          <div className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${colors.bg} ${colors.text} shrink-0`}>
              <IconComponent className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">
                {topic.short_name}
              </span>
              <h3 className="text-sm font-semibold text-text tracking-tight group-hover:text-accent transition-colors leading-snug">
                {topic.name}
              </h3>
            </div>
          </div>

          {/* Question Count Pill */}
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-surface-hover border border-border text-text shrink-0">
            {topic.total_questions} Qs
          </span>
        </div>

        {/* Topic Description */}
        <p className="text-xs text-text-muted line-clamp-2 leading-relaxed mb-3">
          {topic.description}
        </p>

        {/* Subparts Preview Pill list (shows what's grouped inside) */}
        <div className="mb-3 pt-2 border-t border-border/60">
          <div className="text-[10px] uppercase font-mono tracking-wider text-text-muted mb-1 flex items-center gap-1">
            <Layers className="w-3 h-3" />
            <span>Includes {topic.subparts?.length || 0} Subtopics:</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {(topic.subparts || []).map((sp) => (
              <span
                key={sp.id}
                className="text-[10px] px-1.5 py-0.5 rounded bg-bg border border-border/80 text-text-muted truncate max-w-[200px]"
                title={`${sp.id} ${sp.name}`}
              >
                {sp.name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Footer: Difficulty Breakdown & Progress */}
      <div className="pt-2 border-t border-border/60 space-y-2">
        {/* Difficulty Counts Chips */}
        <div className="flex items-center justify-between text-[11px]">
          <div className="flex items-center gap-1.5 text-[10px] font-mono">
            <span className="text-emerald-500 font-medium">E: {topic.difficulty_counts?.Easy || 0}</span>
            <span className="text-text-muted/40">•</span>
            <span className="text-amber-500 font-medium">M: {topic.difficulty_counts?.Medium || 0}</span>
            <span className="text-text-muted/40">•</span>
            <span className="text-rose-500 font-medium">H: {topic.difficulty_counts?.Hard || 0}</span>
          </div>

          {solved > 0 && (
            <div className="flex items-center gap-1 text-[11px] text-emerald-500 font-medium">
              <CheckCircle2 className="w-3 h-3" />
              <span>{solved} Solved</span>
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full bg-border/60 h-1 rounded-full overflow-hidden">
          <div
            className="bg-accent h-full rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Action row */}
        <div className="flex items-center justify-between pt-1">
          <span className="text-[10px] text-text-muted">
            {progressPct}% completed
          </span>

          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent group-hover:translate-x-0.5 transition-transform">
            <span>Start Practice</span>
            <ArrowRight className="w-3 h-3" />
          </span>
        </div>
      </div>
    </div>
  );
};
