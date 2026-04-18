class CefrLevelInfo {
  final String level;
  final String status;
  final int lessonsCount;
  final double hoursSpent;
  final int streakDays;
  final double progressPercent;
  final int practiceSessions;
  final double practiceHours;

  const CefrLevelInfo({
    required this.level,
    required this.status,
    required this.lessonsCount,
    required this.hoursSpent,
    required this.streakDays,
    required this.progressPercent,
    required this.practiceSessions,
    required this.practiceHours,
  });

  factory CefrLevelInfo.fromJson(Map<String, dynamic> json) {
    return CefrLevelInfo(
      level: json['level'] as String,
      status: json['status'] as String,
      lessonsCount: json['lessons_count'] as int,
      hoursSpent: (json['hours_spent'] as num).toDouble(),
      streakDays: json['streak_days'] as int,
      progressPercent: (json['progress_percent'] as num).toDouble(),
      practiceSessions: json['practice_sessions'] as int,
      practiceHours: (json['practice_hours'] as num).toDouble(),
    );
  }
}

class UserLanguageInfo {
  final String id;
  final String languageId;
  final String? teacherPersonaId;
  final String? teachingStyle;
  final String currentCefrLevel;
  final double cefrProgressPercent;

  const UserLanguageInfo({
    required this.id,
    required this.languageId,
    this.teacherPersonaId,
    this.teachingStyle,
    required this.currentCefrLevel,
    required this.cefrProgressPercent,
  });

  factory UserLanguageInfo.fromJson(Map<String, dynamic> json) {
    return UserLanguageInfo(
      id: json['id'] as String,
      languageId: json['language_id'] as String,
      teacherPersonaId: json['teacher_persona_id'] as String?,
      teachingStyle: json['teaching_style'] as String?,
      currentCefrLevel: json['current_cefr_level'] as String,
      cefrProgressPercent:
          (json['cefr_progress_percent'] as num).toDouble(),
    );
  }
}
