import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../models/plan.dart';
import '../../providers/auth_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../widgets/bubble_background.dart';

/// Subscription management screen with plan selection and billing toggle.
class SubscriptionScreen extends ConsumerStatefulWidget {
  const SubscriptionScreen({super.key});

  @override
  ConsumerState<SubscriptionScreen> createState() =>
      _SubscriptionScreenState();
}

class _SubscriptionScreenState extends ConsumerState<SubscriptionScreen> {
  bool _isYearly = false;
  bool _isChanging = false;

  void _navigateTab(BuildContext context, int index) {
    const routes = ['/home', '/practice', '/profile', '/support'];
    if (index < routes.length) context.go(routes[index]);
  }

  Future<void> _changePlan(String planId) async {
    setState(() => _isChanging = true);
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post(
        '/mobile/subscriptions/change',
        data: {
          'plan_id': planId,
          'billing_cycle': _isYearly ? 'yearly' : 'monthly',
        },
      );
      ref.invalidate(currentSubscriptionProvider);
      ref.invalidate(currentPlanProvider);
    } catch (_) {
      // Handle error in production.
    } finally {
      if (mounted) setState(() => _isChanging = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final plan = ref.watch(currentPlanProvider);
    final planName = plan.whenOrNull(data: (p) => p?.name) ?? '';
    final currentPlanId = plan.whenOrNull(data: (p) => p?.id) ?? '';
    final plansAsync = ref.watch(plansProvider);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgProfile,
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 12),

              // Top row
              _buildTopRow(context, planName),

              const SizedBox(height: 20),

              // Billing toggle
              _buildBillingToggle(),

              const SizedBox(height: 16),

              // Plan list
              Expanded(
                child: plansAsync.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (e, _) => Center(child: Text('Error: $e')),
                  data: (plans) => ListView.builder(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: plans.length,
                    itemBuilder: (_, index) {
                      final p = plans[index];
                      final isCurrent = p.id == currentPlanId;
                      return _PlanCard(
                        plan: p,
                        isYearly: _isYearly,
                        isCurrent: isCurrent,
                        isChanging: _isChanging,
                        onSelect: isCurrent
                            ? null
                            : () => _changePlan(p.id),
                      );
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: 2,
        onTap: (i) => _navigateTab(context, i),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Sub-builds
  // ---------------------------------------------------------------------------

  Widget _buildTopRow(BuildContext context, String planName) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Text(
            planName,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          _MenuIcon(
            icon: Icons.person_rounded,
            isActive: false,
            onTap: () => context.go('/profile'),
          ),
          const SizedBox(width: 10),
          _MenuIcon(
            icon: Icons.bar_chart_rounded,
            isActive: false,
            onTap: () => context.push('/profile/cefr'),
          ),
          const SizedBox(width: 10),
          _MenuIcon(
            icon: Icons.history_rounded,
            isActive: false,
            onTap: () => context.push('/profile/history'),
          ),
          const SizedBox(width: 10),
          _MenuIcon(
            icon: Icons.credit_card_rounded,
            isActive: true,
            onTap: () {},
          ),
        ],
      ),
    );
  }

  Widget _buildBillingToggle() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _ToggleChip(
            label: 'Monthly',
            isActive: !_isYearly,
            onTap: () => setState(() => _isYearly = false),
          ),
          const SizedBox(width: 12),
          Column(
            children: [
              _ToggleChip(
                label: 'Yearly',
                isActive: _isYearly,
                onTap: () => setState(() => _isYearly = true),
              ),
              const SizedBox(height: 2),
              const Text(
                'Save up to 20%',
                style: TextStyle(fontSize: 10, color: AppColors.success),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Plan card
// ---------------------------------------------------------------------------

class _PlanCard extends StatelessWidget {
  const _PlanCard({
    required this.plan,
    required this.isYearly,
    required this.isCurrent,
    required this.isChanging,
    this.onSelect,
  });

  final Plan plan;
  final bool isYearly;
  final bool isCurrent;
  final bool isChanging;
  final VoidCallback? onSelect;

  @override
  Widget build(BuildContext context) {
    final price = isYearly ? plan.priceYearly : plan.priceMonthly;
    final cycle = isYearly ? '/yr' : '/mo';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isCurrent
            ? AppColors.primary.withValues(alpha: 0.1)
            : Colors.white.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(16),
        border: isCurrent
            ? Border.all(color: AppColors.primary, width: 2)
            : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                plan.name,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const Spacer(),
              if (isCurrent)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.success,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    'SELECTED',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '\$${price.toStringAsFixed(2)}$cycle',
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
            ),
          ),
          if (isYearly && plan.yearlySavings > 0) ...[
            const SizedBox(height: 4),
            Text(
              'Save ${plan.yearlySavings.toInt()}%',
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: AppColors.success,
              ),
            ),
          ],
          const SizedBox(height: 12),
          // Features summary
          _FeatureRow('Voice', plan.hasVoiceCall
              ? (plan.isUnlimitedVoice ? 'Unlimited' : '${plan.voiceCallLimitMinutes} min')
              : 'Not included'),
          _FeatureRow('Video', plan.hasVideoCall
              ? (plan.isUnlimitedVideo ? 'Unlimited' : '${plan.videoCallLimitMinutes} min')
              : 'Not included'),
          const SizedBox(height: 12),
          if (!isCurrent)
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: isChanging ? null : onSelect,
                child: isChanging
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Select Plan'),
              ),
            ),
        ],
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 13, color: AppColors.textSecondary)),
          const SizedBox(width: 8),
          Text(value,
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Shared widgets
// ---------------------------------------------------------------------------

class _ToggleChip extends StatelessWidget {
  const _ToggleChip({
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  final String label;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        decoration: BoxDecoration(
          color: isActive ? AppColors.primary : AppColors.disabledBg,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: isActive ? Colors.white : AppColors.textSecondary,
          ),
        ),
      ),
    );
  }
}

class _MenuIcon extends StatelessWidget {
  const _MenuIcon({
    required this.icon,
    required this.isActive,
    required this.onTap,
  });

  final IconData icon;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: AppColors.navBg,
          shape: BoxShape.circle,
          border: isActive
              ? Border.all(color: AppColors.navActive, width: 2)
              : null,
        ),
        child: Icon(
          icon,
          color: isActive ? AppColors.navActive : Colors.white70,
          size: 20,
        ),
      ),
    );
  }
}
