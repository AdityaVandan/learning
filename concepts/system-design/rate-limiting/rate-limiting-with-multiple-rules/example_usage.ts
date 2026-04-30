import { MultiRuleRateLimiter, type RateLimitRule } from "./multi-rule-rate-limiter";

type RequestContext = {
  userId: string;
  ip: string;
  endpoint: string;
};

const rules: RateLimitRule<RequestContext>[] = [
  // Burst control: per-user per-endpoint
  {
    id: "per-user-endpoint",
    maxRequests: 10,
    windowMs: 10_000,
    key: (ctx) => `${ctx.userId}::${ctx.endpoint}`,
  },
  // Sustained control: per-user
  {
    id: "per-user",
    maxRequests: 200,
    windowMs: 60_000,
    key: (ctx) => ctx.userId,
  },
  // Abuse control: per-ip
  {
    id: "per-ip",
    maxRequests: 500,
    windowMs: 60_000,
    key: (ctx) => ctx.ip,
  },
];

const limiter = new MultiRuleRateLimiter(rules, { mode: "ALL" });

function handleRequest(ctx: RequestContext) {
  const decision = limiter.take(ctx);

  if (!decision.allowed) {
    // In HTTP you’d typically set:
    // - status: 429
    // - header: Retry-After: ceil(decision.retryAfterMs / 1000)
    // - body: decision.violated (or the most important violated rule)
    return {
      status: 429,
      retryAfterMs: decision.retryAfterMs,
      violatedRules: decision.violated.map((v) => ({
        ruleId: v.ruleId,
        key: v.key,
        resetAtMs: v.resetAtMs,
      })),
    };
  }

  return { status: 200 };
}

// Demo
const ctx: RequestContext = { userId: "u1", ip: "1.2.3.4", endpoint: "GET /v1/items" };
for (let i = 0; i < 12; i++) {
  const res = handleRequest(ctx);
  // eslint-disable-next-line no-console
  console.log(i + 1, res);
}

