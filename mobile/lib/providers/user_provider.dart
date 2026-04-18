import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/plan.dart';
import 'auth_provider.dart';

// ---------------------------------------------------------------------------
// Current subscription
// ---------------------------------------------------------------------------

final currentSubscriptionProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  try {
    final apiClient = ref.watch(apiClientProvider);
    final response = await apiClient.get('/mobile/subscriptions/current');
    return response.data as Map<String, dynamic>;
  } catch (_) {
    return <String, dynamic>{};
  }
});

// ---------------------------------------------------------------------------
// Available plans
// ---------------------------------------------------------------------------

final plansProvider = FutureProvider<List<Plan>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get('/mobile/plans');
  final items = response.data as List<dynamic>;
  return items
      .map((e) => Plan.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ---------------------------------------------------------------------------
// Current plan (derived from subscription + plans)
// ---------------------------------------------------------------------------

final currentPlanProvider = FutureProvider<Plan?>((ref) async {
  try {
    final subscription = await ref.watch(currentSubscriptionProvider.future);
    final allPlans = await ref.watch(plansProvider.future);

    final planId = subscription['plan_id'] as String?;
    if (planId == null) return null;

    for (final plan in allPlans) {
      if (plan.id == planId) return plan;
    }
    return null;
  } catch (_) {
    return null;
  }
});

// ---------------------------------------------------------------------------
// Usage check for a given feature
// ---------------------------------------------------------------------------

final usageCheckProvider =
    FutureProvider.family<Map<String, dynamic>, String>((ref, feature) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get(
    '/mobile/sessions/usage/check',
    queryParameters: {'feature': feature},
  );
  return response.data as Map<String, dynamic>;
});
