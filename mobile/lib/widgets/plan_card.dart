import 'package:flutter/material.dart';

import '../config/theme.dart';

/// Data class representing a subscription plan.
class Plan {
  const Plan({
    required this.name,
    required this.slug,
    required this.priceMonthly,
    required this.priceYearly,
    required this.voiceCallLimitMinutes,
    required this.videoCallLimitMinutes,
    this.features = const [],
  });

  final String name;

  /// One of "free", "pro", "ultra".
  final String slug;

  final double priceMonthly;
  final double priceYearly;

  /// 0 means unlimited.
  final int voiceCallLimitMinutes;

  /// 0 means unlimited.
  final int videoCallLimitMinutes;

  /// Additional feature descriptions to display.
  final List<String> features;
}

/// A card presenting a single [Plan] with pricing and feature list.
class PlanCard extends StatelessWidget {
  const PlanCard({
    super.key,
    required this.plan,
    required this.isYearly,
    this.isSelected = false,
    required this.onSelect,
  });

  final Plan plan;
  final bool isYearly;
  final bool isSelected;
  final VoidCallback onSelect;

  Color get _headerColor {
    switch (plan.slug) {
      case 'pro':
        return AppColors.primary;
      case 'ultra':
        return AppColors.secondary;
      default:
        return AppColors.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final price = isYearly ? plan.priceYearly : plan.priceMonthly;
    final period = isYearly ? '/year' : '/month';
    final priceText = price == 0 ? 'Free' : '\$${price.toStringAsFixed(2)}$period';

    // Build feature list
    final featureLines = <String>[
      ...plan.features,
      plan.voiceCallLimitMinutes == 0 && plan.slug != 'free'
          ? 'Unlimited voice calls'
          : '${plan.voiceCallLimitMinutes} min/day voice calls',
      plan.videoCallLimitMinutes == 0 && plan.slug != 'free'
          ? 'Unlimited video calls'
          : '${plan.videoCallLimitMinutes} min/day video calls',
    ];

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isSelected ? _headerColor : AppColors.divider,
          width: 2,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header bar
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 12),
            color: _headerColor,
            alignment: Alignment.center,
            child: Text(
              plan.name.toUpperCase(),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.2,
              ),
            ),
          ),

          // Body
          Container(
            width: double.infinity,
            color: Colors.white,
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                // Feature list
                ...featureLines.map((f) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle_rounded,
                              color: AppColors.success, size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              f,
                              style: const TextStyle(
                                fontSize: 14,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    )),

                const SizedBox(height: 12),

                // Price
                Text(
                  priceText,
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: _headerColor,
                  ),
                ),

                const SizedBox(height: 16),

                // Action button
                SizedBox(
                  width: double.infinity,
                  child: isSelected
                      ? Container(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: AppColors.success.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Text(
                            'SELECTED',
                            style: TextStyle(
                              color: AppColors.success,
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        )
                      : ElevatedButton(
                          onPressed: onSelect,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _headerColor,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                          child: const Text(
                            'SELECT',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
