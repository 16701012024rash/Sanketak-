import { MaterialIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useRef, useState } from "react";
import {
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AppButton } from "@/components";
import { colors, radius, spacing, touchTarget, typography } from "@/constants";
import { useNetworkStatus } from "@/hooks/use-network-status";
import type { TranslationKey } from "@/i18n";
import { useLanguage } from "@/i18n/use-language";
import { useReportDraft } from "@/report-draft";
import {
  MediaPersistenceError,
  queueReportForOfflineProcessing,
  submitReport,
} from "@/services";

export function SubmitReportScreen() {
  const { t } = useLanguage();
  const { isOnline } = useNetworkStatus();
  const { draft, resetDraft } = useReportDraft();
  const [submitting, setSubmitting] = useState(false);
  const [submitFailed, setSubmitFailed] = useState(false);
  const submissionInFlight = useRef(false);
  const analysis = draft.analysis;

  const methodLabel = t(getMethodLabelKey(draft.reportingMethod));
  const photoStatus = draft.photoUri
    ? t("submit.photoAttached")
    : t("submit.photoNotAdded");

  const handleSubmit = async () => {
    if (submitting || submissionInFlight.current) {
      return;
    }

    submissionInFlight.current = true;
    setSubmitting(true);
    setSubmitFailed(false);

    try {
      const shouldQueue = !isOnline || !draft.analysis;
      const report = shouldQueue
        ? await queueReportForOfflineProcessing(draft)
        : await submitReport(draft);
      resetDraft();
      router.replace({
        pathname: "/report/success",
        params: { reportId: report.id },
      });
    } catch (error) {
      if (error instanceof MediaPersistenceError) {
        setSubmitFailed(true);
        return;
      }

      setSubmitFailed(true);
    } finally {
      submissionInFlight.current = false;
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.content}
        contentInsetAdjustmentBehavior="automatic"
      >
        <View style={styles.header}>
          <Pressable
            accessibilityLabel={t("common.goBack")}
            accessibilityRole="button"
            hitSlop={spacing.md}
            onPress={() => router.back()}
            style={styles.backButton}
          >
            <MaterialIcons color={colors.text} name="chevron-left" size={34} />
          </Pressable>
          <Text style={styles.title}>{t("submit.title")}</Text>
          <View style={styles.headerSpacer} />
        </View>

        <View style={styles.intro}>
          <Text style={styles.heading}>{t("submit.heading")}</Text>
          <Text style={styles.subtitle}>{t("submit.subtitle")}</Text>
        </View>

        <View style={styles.summaryCard}>
          <Text style={styles.cardTitle}>{t("submit.summaryTitle")}</Text>
          <SummaryRow
            icon="notes"
            label={t("submit.observation")}
            value={draft.description || t("submit.notProvided")}
          />
          <SummaryRow
            icon="factory"
            label={t("submit.site")}
            value={draft.site ?? t("submit.notProvided")}
          />
          {draft.area ? (
            <SummaryRow
              icon="domain"
              label={t("submit.area")}
              value={draft.area}
            />
          ) : null}
          <SummaryRow
            icon="record-voice-over"
            label={t("submit.reportMethod")}
            value={methodLabel}
          />
          <SummaryRow
            icon="photo-camera"
            label={t("submit.supportingPhoto")}
            thumbnailUri={draft.photoUri}
            value={photoStatus}
          />
          {analysis?.barrierFailure ? (
            <SummaryRow
              icon="verified-user"
              label={t("submit.safetyConcern")}
              value={analysis.barrierFailure}
            />
          ) : null}
          {analysis?.lifeSavingRules.length ? (
            <SummaryRow
              icon="assignment"
              label={t("submit.lifeSavingRule")}
              value={analysis.lifeSavingRules.join(", ")}
            />
          ) : null}
          {analysis?.potentialConsequence ? (
            <SummaryRow
              icon="warning-amber"
              label={t("submit.potentialConsequence")}
              last
              value={analysis.potentialConsequence}
            />
          ) : null}
        </View>

        <View style={styles.anonymousCard}>
          <View style={styles.anonymousIcon}>
            <MaterialIcons color={colors.white} name="verified-user" size={34} />
          </View>
          <View style={styles.anonymousCopy}>
            <Text style={styles.anonymousTitle}>
              {t("submit.anonymousTitle")}
            </Text>
            <Text style={styles.anonymousSubtitle}>
              {t("submit.anonymousSubtitle")}
            </Text>
          </View>
        </View>

        {!analysis ? (
          <View style={styles.pendingCard}>
            <MaterialIcons color={colors.primary} name="schedule" size={30} />
            <View style={styles.errorCopy}>
              <Text style={styles.pendingTitle}>{t("offline.analysisPending")}</Text>
              <Text style={styles.errorSubtitle}>
                {t("offline.analysisPendingDescription")}
              </Text>
            </View>
          </View>
        ) : null}

        {submitFailed ? (
          <View style={styles.errorCard}>
            <MaterialIcons color={colors.danger} name="error-outline" size={30} />
            <View style={styles.errorCopy}>
              <Text style={styles.errorTitle}>{t("submit.errorTitle")}</Text>
              <Text style={styles.errorSubtitle}>
                {t("submit.errorSubtitle")}
              </Text>
            </View>
          </View>
        ) : null}

        {submitting ? (
          <View style={styles.loadingCard}>
            <Text style={styles.loadingTitle}>{t("submit.submitting")}</Text>
            <Text style={styles.loadingSubtitle}>
              {t("submit.submittingSubtitle")}
            </Text>
          </View>
        ) : null}

        <AppButton
          disabled={submitting}
          loading={submitting}
          onPress={handleSubmit}
          style={styles.submitButton}
          title={submitFailed ? t("submit.tryAgain") : t("submit.submitButton")}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

function SummaryRow({
  icon,
  label,
  last = false,
  thumbnailUri,
  value,
}: {
  icon: keyof typeof MaterialIcons.glyphMap;
  label: string;
  last?: boolean;
  thumbnailUri?: string;
  value: string;
}) {
  return (
    <View style={[styles.summaryRow, last ? styles.summaryRowLast : null]}>
      <View style={styles.rowIconWrap}>
        {thumbnailUri ? (
          <Image source={{ uri: thumbnailUri }} style={styles.thumbnail} />
        ) : (
          <MaterialIcons color={colors.primary} name={icon} size={28} />
        )}
      </View>
      <View style={styles.rowCopy}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.rowValue}>{value}</Text>
      </View>
    </View>
  );
}

function getMethodLabelKey(method: string): TranslationKey {
  if (method === "voice") {
    return "submit.voice";
  }

  if (method === "photo") {
    return "submit.photo";
  }

  return "submit.text";
}

const styles = StyleSheet.create({
  anonymousCard: {
    alignItems: "center",
    backgroundColor: colors.surfaceGreen,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: spacing.lg,
    padding: spacing.lg,
  },
  anonymousCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  anonymousIcon: {
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    height: 58,
    justifyContent: "center",
    width: 58,
  },
  anonymousSubtitle: {
    color: colors.textMuted,
    fontSize: typography.body,
    lineHeight: 23,
  },
  anonymousTitle: {
    color: colors.primaryDark,
    fontSize: typography.subheading,
    fontWeight: "900",
  },
  backButton: {
    alignItems: "center",
    justifyContent: "center",
    minHeight: touchTarget.minHeight,
    width: 48,
  },
  cardTitle: {
    color: colors.text,
    fontSize: typography.subheading,
    fontWeight: "900",
    paddingBottom: spacing.sm,
  },
  content: {
    flexGrow: 1,
    gap: spacing.lg,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  errorCard: {
    alignItems: "flex-start",
    backgroundColor: colors.dangerSoft,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.lg,
  },
  errorCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  errorSubtitle: {
    color: colors.textMuted,
    fontSize: typography.body,
    lineHeight: 22,
  },
  errorTitle: {
    color: colors.danger,
    fontSize: typography.body,
    fontWeight: "900",
  },
  header: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  headerSpacer: {
    width: 48,
  },
  heading: {
    color: colors.primaryDark,
    fontSize: typography.title,
    fontWeight: "900",
    lineHeight: 34,
  },
  intro: {
    gap: spacing.sm,
  },
  loadingCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    gap: spacing.xs,
    padding: spacing.lg,
  },
  loadingSubtitle: {
    color: colors.textMuted,
    fontSize: typography.body,
  },
  loadingTitle: {
    color: colors.text,
    fontSize: typography.body,
    fontWeight: "900",
  },
  pendingCard: {
    alignItems: "flex-start",
    backgroundColor: colors.surfaceGreen,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.lg,
  },
  pendingTitle: {
    color: colors.primaryDark,
    fontSize: typography.body,
    fontWeight: "900",
  },
  rowCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  rowIconWrap: {
    alignItems: "center",
    backgroundColor: colors.surfaceGreen,
    borderRadius: radius.md,
    height: 48,
    justifyContent: "center",
    overflow: "hidden",
    width: 48,
  },
  rowLabel: {
    color: colors.textMuted,
    fontSize: typography.caption,
    fontWeight: "800",
  },
  rowValue: {
    color: colors.text,
    fontSize: typography.body,
    fontWeight: "700",
    lineHeight: 23,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  submitButton: {
    borderRadius: radius.lg,
    marginTop: "auto",
    minHeight: 60,
  },
  subtitle: {
    color: colors.text,
    fontSize: typography.body,
    lineHeight: 24,
  },
  summaryCard: {
    backgroundColor: colors.white,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    overflow: "hidden",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  summaryRow: {
    alignItems: "center",
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: "row",
    gap: spacing.md,
    paddingVertical: spacing.md,
  },
  summaryRowLast: {
    borderBottomWidth: 0,
  },
  thumbnail: {
    height: "100%",
    width: "100%",
  },
  title: {
    color: colors.text,
    flex: 1,
    fontSize: typography.heading,
    fontWeight: "900",
    textAlign: "center",
  },
});
