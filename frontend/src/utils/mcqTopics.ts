/**
 * Centralized Broad Topic Mapping and Metadata for MCQ Question Bank.
 * Single source of truth on the frontend, exactly matching broad_topics_map.json.
 */

export interface BroadTopicMeta {
  id: string;
  name: string;
  short_name: string;
  description: string;
  icon: string;
  color: string;
  subpartIds: string[];
}

export const MCQ_BROAD_TOPICS: BroadTopicMeta[] = [
  {
    id: 'os',
    name: 'Operating Systems',
    short_name: 'OS',
    description: 'CPU scheduling, concurrency, deadlocks, memory virtualization, paging, storage, file systems, and disk scheduling.',
    icon: 'Cpu',
    color: 'sky',
    subpartIds: ['1.1.1', '1.1.2', '1.1.3', '1.1.4']
  },
  {
    id: 'dbms',
    name: 'Database Management Systems',
    short_name: 'DBMS',
    description: 'Relational schema design, normalization, ACID transactions, concurrency control, B+ trees, indexing, and SQL queries.',
    icon: 'Database',
    color: 'emerald',
    subpartIds: ['1.2.1', '1.2.2', '1.2.3', '1.2.4']
  },
  {
    id: 'computer-networks',
    name: 'Computer Networks',
    short_name: 'Networks',
    description: 'OSI & TCP/IP models, data link framing, IP routing (CIDR, OSPF, BGP), TCP flow & congestion control, HTTP, DNS, and TLS security.',
    icon: 'Network',
    color: 'indigo',
    subpartIds: ['1.3.1', '1.3.2', '1.3.3', '1.3.4']
  },
  {
    id: 'oop',
    name: 'Object-Oriented Programming',
    short_name: 'OOP',
    description: 'Encapsulation, inheritance, runtime polymorphism, dynamic dispatch, constructors, destructor lifecycle, and tricky output prediction.',
    icon: 'Boxes',
    color: 'purple',
    subpartIds: ['1.4.1', '1.4.2', '1.4.3', '1.4.4']
  },
  {
    id: 'dsa',
    name: 'Data Structures & Algorithms',
    short_name: 'DSA',
    description: 'Asymptotic complexity (Master Theorem, recurrences), linked lists, stacks, queues, binary search trees, heaps, graphs, searching & sorting.',
    icon: 'Binary',
    color: 'amber',
    subpartIds: ['2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7']
  },
  {
    id: 'pseudocode',
    name: 'Pseudocode & Code Analysis',
    short_name: 'Pseudocode',
    description: 'Bitwise manipulation, operator precedence, loop invariant execution, nested loop traces, and recursive dry-run analysis.',
    icon: 'FileCode2',
    color: 'cyan',
    subpartIds: ['3.1', '3.2', '3.3']
  },
  {
    id: 'applied-systems',
    name: 'Software Engineering & Systems',
    short_name: 'Systems',
    description: 'Cloud computing architectures, software engineering principles, Git version control internals, Linux shell scripting, and REST APIs.',
    icon: 'Terminal',
    color: 'orange',
    subpartIds: ['4.1', '4.2', '4.3', '4.4']
  },
  {
    id: 'data-science',
    name: 'Data Science & Machine Learning',
    short_name: 'Data Science',
    description: 'Probability theory, hypothesis testing (z/t/ANOVA), supervised learning, bias-variance tradeoff, regularization (L1/L2), Pandas & NumPy operations.',
    icon: 'LineChart',
    color: 'rose',
    subpartIds: ['5.1', '5.2', '5.3', '5.4', '5.5']
  },
  {
    id: 'aptitude',
    name: 'Aptitude & Logical Reasoning',
    short_name: 'Aptitude',
    description: 'Quantitative arithmetic (work, time, speed, interest), combinatorics, modern mathematics, syllogisms, circular seating, and verbal comprehension.',
    icon: 'Brain',
    color: 'violet',
    subpartIds: ['6.1', '6.2', '6.3', '6.4']
  }
];

export const SUBPART_TO_BROAD_TOPIC_ID: Record<string, string> = {};
export const SUBPART_TO_BROAD_TOPIC_NAME: Record<string, string> = {};

MCQ_BROAD_TOPICS.forEach(topic => {
  topic.subpartIds.forEach(spId => {
    SUBPART_TO_BROAD_TOPIC_ID[spId] = topic.id;
    SUBPART_TO_BROAD_TOPIC_NAME[spId] = topic.name;
  });
});

export function getBroadTopicForSubpart(subpartId: string): BroadTopicMeta | undefined {
  const topicId = SUBPART_TO_BROAD_TOPIC_ID[subpartId];
  return MCQ_BROAD_TOPICS.find(t => t.id === topicId);
}

export function getTopicColorClasses(color: string): { bg: string; text: string; border: string; ring: string } {
  switch (color) {
    case 'sky':
      return { bg: 'bg-sky-500/10', text: 'text-sky-500', border: 'border-sky-500/30', ring: 'ring-sky-500/20' };
    case 'emerald':
      return { bg: 'bg-emerald-500/10', text: 'text-emerald-500', border: 'border-emerald-500/30', ring: 'ring-emerald-500/20' };
    case 'indigo':
      return { bg: 'bg-indigo-500/10', text: 'text-indigo-500', border: 'border-indigo-500/30', ring: 'ring-indigo-500/20' };
    case 'purple':
      return { bg: 'bg-purple-500/10', text: 'text-purple-500', border: 'border-purple-500/30', ring: 'ring-purple-500/20' };
    case 'amber':
      return { bg: 'bg-amber-500/10', text: 'text-amber-500', border: 'border-amber-500/30', ring: 'ring-amber-500/20' };
    case 'cyan':
      return { bg: 'bg-cyan-500/10', text: 'text-cyan-500', border: 'border-cyan-500/30', ring: 'ring-cyan-500/20' };
    case 'orange':
      return { bg: 'bg-orange-500/10', text: 'text-orange-500', border: 'border-orange-500/30', ring: 'ring-orange-500/20' };
    case 'rose':
      return { bg: 'bg-rose-500/10', text: 'text-rose-500', border: 'border-rose-500/30', ring: 'ring-rose-500/20' };
    case 'violet':
      return { bg: 'bg-violet-500/10', text: 'text-violet-500', border: 'border-violet-500/30', ring: 'ring-violet-500/20' };
    default:
      return { bg: 'bg-accent/10', text: 'text-accent', border: 'border-accent/30', ring: 'ring-accent/20' };
  }
}
