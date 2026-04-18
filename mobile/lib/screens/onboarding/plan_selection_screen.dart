import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../models/plan.dart';
import '../../providers/auth_provider.dart';
import '../../providers/plan_provider.dart';
import '../../widgets/bubble_background.dart';

class PlanSelectionScreen extends ConsumerStatefulWidget {
  const PlanSelectionScreen({super.key});

  @override
  ConsumerState<PlanSelectionScreen> createState() =>
      _PlanSelectionScreenState();
}

class _PlanSelectionScreenState extends ConsumerState<PlanSelectionScreen> {
  bool _isYearly = true;
  String? _selectedPlanId;
  bool _isSubmitting = false;

  Future<void> _selectPlan(Plan plan) async {
    setState(() {
      _selectedPlanId = plan.id;
      _isSubmitting = true;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post('/mobile/subscriptions', data: {
        'plan_id': plan.id,
        'billing_cycle': _isYearly ? 'yearly' : 'monthly',
      });

      ref.read(authProvider.notifier).completeOnboarding();

      if (mounted) {
        context.go('/home');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSubmitting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to subscribe: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final plansAsync = ref.watch(plansProvider);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgOnboarding,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 32),

                // Title
                Text(
                  'Choose Your Plan',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 24),

                // Monthly / Yearly toggle
                Row(
                  children: [
                    Text(
                      'Monthly',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: _isYearly
                                ? AppColors.textMuted
                                : AppColors.textPrimary,
                          ),
                    ),
                    const SizedBox(width: 8),
                    Switch(
                      value: _isYearly,
                      activeColor: AppColors.primary,
                      onChanged: (value) =>
                          setState(() => _isYearly = value),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Yearly',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: _isYearly
                                ? AppColors.textPrimary
                                : AppColors.textMuted,
                          ),
                    ),
                  ],
                ),

                // Savings hint for yearly
                if (_isYearly)
                  plansAsync.whenOrNull(
                        data: (plans) {
                          // Show savings from the highest-tier (ultra) plan
                          final ultra = plans.isNotEmpty ? plans.last : null;
                          if (ultra == null || ultra.yearlySavings <= 0) {
                            return const SizedBox.shrink();
                          }
                          return Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Text(
                              'Save ${ultra.yearlySavings.toStringAsFixed(0)}% with yearly billing',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: AppColors.success),
                            ),
                          );
                        },
                      ) ??
                      const SizedBox.shrink(),
                const SizedBox(height: 24),

                // Plan cards
                Expanded(
                  child: plansAsync.when(
                    data: (plans) => ListView.separated(
                      itemCount: plans.length,
                      separatorBuilder: (_, __) =>
                          const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final plan = plans[index];
                        return _PlanCard(
                          plan: plan,
                          isYearly: _isYearly,
                          isSelected: _selectedPlanId == plan.id,
                          isSubmitting:
                              _isSubmitting && _selectedPlanId == plan.id,
                          onTap: _isSubmitting
                              ? null
                              : () => _selectPlan(plan),
                        );
                      },
                    ),
                    loading: () => const Center(
                      child: CircularProgressIndicator(),
                    ),
                    error: (error, _) => Center(
                      child: Text(
                        'Failed to load plans: $error',
                        style: Theme.of(context)
                            .textTheme
                            .bodyMedium
                            ?.copyWith(color: AppColors.error),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Plan card widget
// ---------------------------------------------------------------------------

class _PlanCard extends StatelessWidget {
  final Plan plan;
  final bool isYearly;
  final bool isSelected;
  final bool isSubmitting;
  final VoidCallback? onTap;

  const _PlanCard({
    required this.plan,
    required this.isYearly,
    required this.isSelected,
    required this.isSubmitting,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final price = isYearly
        ? (plan.priceYearly / 12)
        : plan.priceMonthly;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.cardBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? AppColors.primary : AppColors.divider,
            width: isSelected ? 2 : 1,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: AppColors.primary.withOpacity(0.15),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Plan name + price
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  plan.name,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                if (isSubmitting)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                else
                  Text(
                    '\$${price.toStringAsFixed(2)}/mo',
                    style:
                        Theme.of(context).textTheme.headlineMedium?.copyWith(
                              color: AppColors.primary,
                            ),
                  ),
              ],
            ),
            const SizedBox(height: 8),

            // Feature summary
            _featureRow(
              context,
              Icons.chat_bubble_outline,
              'Text: ${plan.textLearningLimitMinutes == -1 ? 'Unlimited' : '${plan.textLearningLimitMinutes} min'}',
            ),
            const SizedBox(height: 4),
            _featureRow(
              context,
              Icons.mic_none,
              'Voice: ${plan.isUnlimitedVoice ? 'Unlimited' : '${plan.voiceCallLimitMinutes} min'}',
            ),
            const SizedBox(height: 4),
            _featureRow(
              context,
              Icons.videocam_outlined,
              'Video: ${plan.isUnlimitedVideo ? 'Unlimited' : '${plan.videoCallLimitMinutes} min'}',
            ),
          ],
        ),
      ),
    );
  }

  Widget _featureRow(BuildContext context, IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, size: 16, color: AppColors.textSecondary),
        const SizedBox(width: 8),
        Text(text, style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }
}
