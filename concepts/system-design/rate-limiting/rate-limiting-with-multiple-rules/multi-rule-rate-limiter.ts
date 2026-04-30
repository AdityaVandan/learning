export type RateLimitMode = "ALL" | "ANY";

export type RuleKeyFn<TContext> = (ctx: TContext) => string;

export interface RateLimitRule<TContext> {
  /**
   * Stable identifier for observability and debugging.
   * Examples: "per-user", "per-ip", "per-user-endpoint", "global"
   */
  id: string;

  /** Maximum requests allowed within the window. Must be >= 1. */
  maxRequests: number;

  /** Window length in milliseconds. Must be >= 1. */
  windowMs: number;

  /** Determines which bucket the request hits for this rule. */
  key: RuleKeyFn<TContext>;
}

export interface RuleDecision {
  ruleId: string;
  key: string;
  allowed: boolean;
  remaining: number;
  resetAtMs: number;
  retryAfterMs: number;
}

export interface RateLimitDecision {
  allowed: boolean;
  mode: RateLimitMode;
  nowMs: number;
  retryAfterMs: number;
  violated: RuleDecision[];
  perRule: RuleDecision[];
}

type FixedWindowState = {
  windowStartMs: number;
  count: number;
};

/**
 * In-memory fixed-window store.
 *
 * Notes:
 * - This is process-local only (not shared across instances).
 * - Fixed window is simple and fast but has boundary effects.
 * - Intended as a learning/reference implementation.
 */
export class InMemoryFixedWindowStore {
  private readonly buckets = new Map<string, FixedWindowState>();

  get(bucketId: string): FixedWindowState | undefined {
    return this.buckets.get(bucketId);
  }

  set(bucketId: string, state: FixedWindowState): void {
    this.buckets.set(bucketId, state);
  }
}

export class MultiRuleRateLimiter<TContext> {
  constructor(
    private readonly rules: RateLimitRule<TContext>[],
    private readonly opts?: { mode?: RateLimitMode; store?: InMemoryFixedWindowStore }
  ) {
    if (this.rules.length === 0) {
      throw new Error("MultiRuleRateLimiter requires at least one rule");
    }
    for (const r of this.rules) {
      if (!r.id) throw new Error("Rule.id is required");
      if (!Number.isFinite(r.maxRequests) || r.maxRequests < 1) {
        throw new Error(`Rule.maxRequests must be >= 1 (rule: ${r.id})`);
      }
      if (!Number.isFinite(r.windowMs) || r.windowMs < 1) {
        throw new Error(`Rule.windowMs must be >= 1 (rule: ${r.id})`);
      }
      if (typeof r.key !== "function") {
        throw new Error(`Rule.key must be a function (rule: ${r.id})`);
      }
    }
  }

  private get mode(): RateLimitMode {
    return this.opts?.mode ?? "ALL";
  }

  private get store(): InMemoryFixedWindowStore {
    return this.opts?.store ?? (this._defaultStore ??= new InMemoryFixedWindowStore());
  }
  private _defaultStore?: InMemoryFixedWindowStore;

  /**
   * Evaluate without mutating counters.
   */
  peek(ctx: TContext, nowMs: number = Date.now()): RateLimitDecision {
    const perRule = this.rules.map((rule) => this.peekRule(rule, ctx, nowMs));
    return this.combine(perRule, nowMs);
  }

  /**
   * Evaluate and, if allowed, consume capacity in all applicable rules.
   *
   * In a distributed system, you'd typically want an atomic "check+consume"
   * (e.g., Redis Lua) to avoid partial updates.
   */
  take(ctx: TContext, nowMs: number = Date.now()): RateLimitDecision {
    const perRule = this.rules.map((rule) => this.peekRule(rule, ctx, nowMs));
    const decision = this.combine(perRule, nowMs);
    if (!decision.allowed) return decision;

    for (const rule of this.rules) {
      this.consumeRule(rule, ctx, nowMs);
    }

    // Recompute so remaining/reset are accurate after consumption.
    const after = this.rules.map((rule) => this.peekRule(rule, ctx, nowMs));
    return this.combine(after, nowMs);
  }

  private bucketId(ruleId: string, key: string): string {
    return `${ruleId}::${key}`;
  }

  private currentWindowStart(nowMs: number, windowMs: number): number {
    return Math.floor(nowMs / windowMs) * windowMs;
  }

  private peekRule(rule: RateLimitRule<TContext>, ctx: TContext, nowMs: number): RuleDecision {
    const key = rule.key(ctx);
    const bucketId = this.bucketId(rule.id, key);
    const windowStartMs = this.currentWindowStart(nowMs, rule.windowMs);
    const resetAtMs = windowStartMs + rule.windowMs;

    const state = this.store.get(bucketId);
    const count = state && state.windowStartMs === windowStartMs ? state.count : 0;
    const remaining = Math.max(0, rule.maxRequests - count);
    const allowed = count < rule.maxRequests;
    const retryAfterMs = allowed ? 0 : Math.max(0, resetAtMs - nowMs);

    return {
      ruleId: rule.id,
      key,
      allowed,
      remaining,
      resetAtMs,
      retryAfterMs,
    };
  }

  private consumeRule(rule: RateLimitRule<TContext>, ctx: TContext, nowMs: number): void {
    const key = rule.key(ctx);
    const bucketId = this.bucketId(rule.id, key);
    const windowStartMs = this.currentWindowStart(nowMs, rule.windowMs);

    const state = this.store.get(bucketId);
    if (!state || state.windowStartMs !== windowStartMs) {
      this.store.set(bucketId, { windowStartMs, count: 1 });
      return;
    }
    this.store.set(bucketId, { windowStartMs, count: state.count + 1 });
  }

  private combine(perRule: RuleDecision[], nowMs: number): RateLimitDecision {
    const mode = this.mode;
    const violated = perRule.filter((d) => !d.allowed);

    const allowed =
      mode === "ALL"
        ? violated.length === 0
        : // ANY: allow if at least one rule allows
          perRule.some((d) => d.allowed);

    const retryAfterMs =
      allowed || violated.length === 0
        ? 0
        : mode === "ALL"
          ? Math.max(...violated.map((v) => v.retryAfterMs))
          : Math.min(...violated.map((v) => v.retryAfterMs));

    return {
      allowed,
      mode,
      nowMs,
      retryAfterMs,
      violated,
      perRule,
    };
  }
}

