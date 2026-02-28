"use client";

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../context/AuthContext';
import { TerraformPlanWithDeployments } from '@/types/deployment';
import { PlanCard } from '@/components/PlanCard';
import { DeploymentList } from '@/components/DeploymentList';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

type FilterStatus = 'all' | 'success' | 'failed' | 'running' | 'not_deployed';
type SortOption = 'newest' | 'oldest' | 'most_deployments';

const STATUS_CONFIG = {
    all: { label: 'All', dot: 'bg-slate-400', ring: 'ring-slate-400/30', active: 'bg-slate-800 text-white' },
    success: { label: 'Succeeded', dot: 'bg-emerald-400', ring: 'ring-emerald-400/30', active: 'bg-emerald-500/20 text-emerald-300' },
    failed: { label: 'Failed', dot: 'bg-red-400', ring: 'ring-red-400/30', active: 'bg-red-500/20 text-red-300' },
    running: { label: 'Running', dot: 'bg-amber-400', ring: 'ring-amber-400/30', active: 'bg-amber-500/20 text-amber-300' },
    not_deployed: { label: 'Not Deployed', dot: 'bg-slate-600', ring: 'ring-slate-600/30', active: 'bg-slate-700/50 text-slate-400' },
};

export default function HistoryPage() {
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();

    const [plans, setPlans] = useState<TerraformPlanWithDeployments[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedPlanIds, setExpandedPlanIds] = useState<Set<string>>(new Set());
    const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
    const [sortOption, setSortOption] = useState<SortOption>('newest');
    const [searchQuery, setSearchQuery] = useState('');
    const [mounted, setMounted] = useState(false);

    useEffect(() => { setMounted(true); }, []);

    useEffect(() => {
        if (!authLoading && !user) router.push('/auth');
    }, [authLoading, user, router]);

    useEffect(() => {
        if (user?.sub) fetchHistory();
    }, [user?.sub]);

    const fetchHistory = async () => {
        if (!user?.sub) return;
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE_URL}/api/user/${user.sub}/history`);
            if (response.status === 401) { router.push('/auth'); return; }
            if (response.status === 500) throw new Error('Server error occurred. Please try again later.');
            if (!response.ok) throw new Error('Failed to load deployment history');
            const data = await response.json();
            setPlans(data.plans || []);
        } catch (err: any) {
            setError(err.message || 'Failed to load deployment history. Please check your connection.');
        } finally {
            setLoading(false);
        }
    };

    const filteredAndSortedPlans = useMemo(() => {
        let filtered = plans;
        if (filterStatus !== 'all') {
            filtered = filtered.filter(plan => {
                if (filterStatus === 'not_deployed') return !plan.latest_deployment_status;
                return plan.latest_deployment_status === filterStatus;
            });
        }
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            filtered = filtered.filter(p => p.original_requirements.toLowerCase().includes(q));
        }
        const sorted = [...filtered];
        if (sortOption === 'newest') sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        else if (sortOption === 'oldest') sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
        else sorted.sort((a, b) => b.deployment_count - a.deployment_count);
        return sorted;
    }, [plans, filterStatus, sortOption, searchQuery]);

    const togglePlan = (planId: string) => {
        setExpandedPlanIds(prev => {
            const next = new Set(prev);
            next.has(planId) ? next.delete(planId) : next.add(planId);
            return next;
        });
    };

    const statusCounts = useMemo(() => ({
        all: plans.length,
        success: plans.filter(p => p.latest_deployment_status === 'success').length,
        failed: plans.filter(p => p.latest_deployment_status === 'failed' || p.latest_deployment_status === 'destroy_failed').length,
        running: plans.filter(p => p.latest_deployment_status === 'running' || p.latest_deployment_status === 'started').length,
        not_deployed: plans.filter(p => !p.latest_deployment_status).length,
    }), [plans]);

    const allExpanded = filteredAndSortedPlans.length > 0 && filteredAndSortedPlans.every(p => expandedPlanIds.has(p.id));

    // ─── Loading ────────────────────────────────────────────────────────────
    if (authLoading || loading) {
        return (
            <div className="min-h-screen bg-[#080C14] flex items-center justify-center">
                <div className="flex flex-col items-center gap-5">
                    <div className="relative h-12 w-12">
                        <div className="absolute inset-0 rounded-full border border-indigo-500/20" />
                        <div className="absolute inset-0 rounded-full border-t border-indigo-400 animate-spin" />
                        <div className="absolute inset-2 rounded-full border-t border-fuchsia-400 animate-spin [animation-duration:0.7s] [animation-direction:reverse]" />
                    </div>
                    <p className="text-[13px] tracking-widest text-slate-500 uppercase font-medium">Loading history</p>
                </div>
            </div>
        );
    }

    // ─── Error ───────────────────────────────────────────────────────────────
    if (error) {
        return (
            <div className="min-h-screen bg-[#080C14] flex items-center justify-center px-6">
                <div className="max-w-sm w-full">
                    <div className="relative rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-b from-red-500/5 to-transparent pointer-events-none" />
                        <div className="text-3xl mb-4">⚠</div>
                        <p className="text-sm text-red-300/80 mb-6 leading-relaxed">{error}</p>
                        <button onClick={fetchHistory} className="inline-flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 px-5 py-2.5 text-sm font-medium text-red-300 transition-all duration-200">
                            Try again
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // ─── Empty (no plans at all) ─────────────────────────────────────────────
    if (plans.length === 0) {
        return (
            <div className="min-h-screen bg-[#080C14] flex items-center justify-center px-6">
                <div className="max-w-sm w-full text-center">
                    <div className="mx-auto mb-6 h-16 w-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 border border-white/5 flex items-center justify-center text-3xl">
                        📋
                    </div>
                    <h2 className="text-xl font-semibold text-slate-200 mb-2 tracking-tight">No plans yet</h2>
                    <p className="text-sm text-slate-500 mb-8 leading-relaxed">Create your first infrastructure plan to see it appear here.</p>
                    <button
                        onClick={() => router.push('/generate')}
                        className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 hover:bg-indigo-400 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all duration-200 hover:-translate-y-0.5"
                    >
                        <span className="text-base leading-none">+</span> New Plan
                    </button>
                </div>
            </div>
        );
    }

    // ─── Main ────────────────────────────────────────────────────────────────
    return (
        <div
            className="min-h-screen bg-[#080C14] text-slate-100"
            style={{ opacity: mounted ? 1 : 0, transition: 'opacity 0.4s ease' }}
        >
            {/* Ambient glow */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden">
                <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-indigo-600/8 blur-3xl" />
                <div className="absolute top-1/3 right-0 h-72 w-72 rounded-full bg-fuchsia-600/6 blur-3xl" />
            </div>

            <div className="relative max-w-5xl mx-auto px-6 pt-10 pb-20">

                {/* ── Title row ── */}
                <div className="flex items-end justify-between mb-10">
                    <div>
                        <p className="text-[11px] tracking-[0.2em] text-indigo-400/60 uppercase font-medium mb-2">Infrastructure</p>
                        <h1 className="text-3xl font-semibold tracking-tight text-slate-100">
                            Deployment History
                        </h1>
                    </div>
                    <button
                        onClick={() => router.push('/generate')}
                        className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 hover:bg-indigo-400 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
                    >
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
                        New Plan
                    </button>
                </div>

                {/* ── Toolbar ── */}
                <div className="mb-6 space-y-3">
                    {/* Search */}
                    <div className="relative">
                        <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" width="15" height="15" viewBox="0 0 15 15" fill="none">
                            <path d="M10 6.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Zm-.682 3.56 2.56 2.56-.707.707-2.56-2.56a4.5 4.5 0 1 1 .707-.707Z" fill="currentColor" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Search by requirements…"
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="w-full rounded-xl border border-white/6 bg-white/[0.03] pl-10 pr-10 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500/40 focus:border-indigo-500/30 transition-all duration-200"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery('')}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                            >
                                <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="m2 2 10 10M12 2 2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                            </button>
                        )}
                    </div>

                    {/* Filters + sort row */}
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                        {/* Status pills */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                            {(Object.entries(STATUS_CONFIG) as [FilterStatus, typeof STATUS_CONFIG['all']][]).map(([key, cfg]) => {
                                const count = statusCounts[key];
                                const active = filterStatus === key;
                                return (
                                    <button
                                        key={key}
                                        onClick={() => setFilterStatus(key)}
                                        className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-150 ${active
                                            ? `${cfg.active} ring-1 ${cfg.ring}`
                                            : 'text-slate-500 hover:text-slate-300 bg-white/[0.03] border border-white/5 hover:border-white/10'
                                            }`}
                                    >
                                        <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot} ${key === 'running' && active ? 'animate-pulse' : ''}`} />
                                        {cfg.label}
                                        <span className={`rounded-md px-1 py-px text-[10px] ${active ? 'bg-white/10' : 'bg-white/5'}`}>{count}</span>
                                    </button>
                                );
                            })}
                        </div>

                        {/* Right controls */}
                        <div className="flex items-center gap-2">
                            <select
                                value={sortOption}
                                onChange={e => setSortOption(e.target.value as SortOption)}
                                className="rounded-lg border border-white/6 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400 focus:outline-none cursor-pointer hover:border-white/10 transition-colors"
                            >
                                <option value="newest">Newest first</option>
                                <option value="oldest">Oldest first</option>
                                <option value="most_deployments">Most deployments</option>
                            </select>

                            <button
                                onClick={() => allExpanded
                                    ? setExpandedPlanIds(new Set())
                                    : setExpandedPlanIds(new Set(filteredAndSortedPlans.map(p => p.id)))
                                }
                                className="rounded-lg border border-white/6 bg-white/[0.03] hover:border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-all duration-150 inline-flex items-center gap-1.5"
                            >
                                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className={`transition-transform duration-200 ${allExpanded ? 'rotate-180' : ''}`}>
                                    <path d="M1 4l5 4 5-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                                {allExpanded ? 'Collapse all' : 'Expand all'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* ── Result count ── */}
                <p className="text-[11px] text-slate-600 mb-4 tracking-wide">
                    {filteredAndSortedPlans.length === 0
                        ? 'No results'
                        : `${filteredAndSortedPlans.length} ${filteredAndSortedPlans.length === 1 ? 'plan' : 'plans'}${searchQuery ? ' found' : ''}`
                    }
                </p>

                {/* ── Plan list ── */}
                {filteredAndSortedPlans.length === 0 ? (
                    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-12 text-center">
                        <p className="text-sm text-slate-500 mb-4">No plans match your current filters.</p>
                        <button
                            onClick={() => { setSearchQuery(''); setFilterStatus('all'); }}
                            className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors underline underline-offset-2"
                        >
                            Clear filters
                        </button>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {filteredAndSortedPlans.map((plan, i) => {
                            const isExpanded = expandedPlanIds.has(plan.id);
                            return (
                                <div
                                    key={plan.id}
                                    style={{
                                        animationDelay: `${i * 40}ms`,
                                        animation: 'fadeUp 0.35s ease both',
                                    }}
                                >
                                    {/* Plan row */}
                                    <div className={`rounded-xl border transition-all duration-200 overflow-hidden ${isExpanded
                                        ? 'border-indigo-500/20 bg-white/[0.04] shadow-lg shadow-indigo-500/5'
                                        : 'border-white/5 bg-white/[0.02] hover:border-white/10 hover:bg-white/[0.03]'
                                        }`}>
                                        <PlanCard
                                            plan={plan}
                                            isExpanded={isExpanded}
                                            onToggle={() => togglePlan(plan.id)}
                                        />

                                        {/* Deployments */}
                                        <div
                                            style={{
                                                display: 'grid',
                                                gridTemplateRows: isExpanded ? '1fr' : '0fr',
                                                transition: 'grid-template-rows 0.25s ease',
                                            }}
                                        >
                                            <div className="overflow-hidden">
                                                {isExpanded && (
                                                    <div className="border-t border-white/5">
                                                        <DeploymentList deployments={plan.deployments} />
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            <style>{`
                @keyframes fadeUp {
                    from { opacity: 0; transform: translateY(10px); }
                    to   { opacity: 1; transform: translateY(0);    }
                }
            `}</style>
        </div>
    );
}