import 'package:flutter/material.dart';

import '../config/theme.dart';

/// Horizontal info bar showing language flag, CEFR level, progress, and plan.
class TopInfoBar extends StatelessWidget {
  const TopInfoBar({
    super.key,
    this.languageFlag,
    required this.cefrLevel,
    required this.progressPercent,
    required this.planName,
    this.onLanguageTap,
  });

  /// URL or asset path for the language flag image. Falls back to an icon.
  final String? languageFlag;

  /// Current CEFR level (e.g. "B1").
  final String cefrLevel;

  /// Overall progress 0–100.
  final int progressPercent;

  /// Name of the active subscription plan (e.g. "Pro").
  final String planName;

  /// Called when the language flag button is tapped.
  final VoidCallback? onLanguageTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          // Language flag button
          GestureDetector(
            onTap: onLanguageTap,
            child: Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppColors.navBg,
                borderRadius: BorderRadius.circular(8),
              ),
              child: _buildFlag(),
            ),
          ),
          const SizedBox(width: 12),

          // CEFR level
          Text(
            cefrLevel,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(width: 8),

          // Progress percentage
          Text(
            '$progressPercent%',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: AppColors.textMuted,
            ),
          ),

          const Spacer(),

          // Plan chip
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.accent.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              planName,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFlag() {
    if (languageFlag != null && languageFlag!.isNotEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: Image.network(
          languageFlag!,
          width: 28,
          height: 20,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => const Icon(
            Icons.flag_rounded,
            size: 22,
            color: Colors.white,
          ),
        ),
      );
    }
    return const Icon(
      Icons.flag_rounded,
      size: 22,
      color: Colors.white,
    );
  }
}
