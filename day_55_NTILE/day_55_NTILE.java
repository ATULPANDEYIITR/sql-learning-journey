import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

public class NtileSegmentation {

    enum SegmentationType {
        QUARTILE(4),
        DECILE(10);

        private final int bucketCount;

        SegmentationType(int bucketCount) {
            this.bucketCount = bucketCount;
        }

        public int bucketCount() {
            return bucketCount;
        }
    }

    record Record(int id, String customer, double score) {
        public Record {
            if (id <= 0) {
                throw new IllegalArgumentException(
                    "id must be positive"
                );
            }

            if (customer == null || customer.isBlank()) {
                throw new IllegalArgumentException(
                    "customer must not be blank"
                );
            }

            if (!Double.isFinite(score)) {
                throw new IllegalArgumentException(
                    "score must be finite"
                );
            }
        }
    }

    record BucketedRecord(
        Record record,
        int bucket,
        int bucketCount
    ) {}

    record BucketStatistics(
        int bucket,
        int count,
        double minimum,
        double maximum,
        double average
    ) {}

    interface BucketPolicy {
        String label(int bucket);
    }

    static final class DecilePolicy implements BucketPolicy {
        private static final Map<Integer, String> LABELS = Map.of(
            1, "Top 10%",
            2, "High",
            3, "High",
            4, "Upper-Middle",
            5, "Upper-Middle",
            6, "Lower-Middle",
            7, "Lower-Middle",
            8, "Low",
            9, "Low",
            10, "Bottom 10%"
        );

        @Override
        public String label(int bucket) {
            return Objects.requireNonNull(
                LABELS.get(bucket),
                "Unknown decile"
            );
        }
    }

    static final class NtileService {

        List<BucketedRecord> assign(
            List<Record> source,
            int bucketCount
        ) {
            validateBucketCount(bucketCount);

            List<Record> ordered = new ArrayList<>(source);

            ordered.sort(
                Comparator.comparingDouble(Record::score)
                    .reversed()
                    .thenComparingInt(Record::id)
            );

            int total = ordered.size();

            if (total == 0) {
                return List.of();
            }

            int baseSize = total / bucketCount;
            int remainder = total % bucketCount;

            List<BucketedRecord> result =
                new ArrayList<>(total);

            int position = 0;

            for (int bucket = 1;
                 bucket <= bucketCount;
                 bucket++) {

                int size =
                    baseSize + (bucket <= remainder ? 1 : 0);

                for (int i = 0;
                     i < size && position < total;
                     i++) {

                    result.add(
                        new BucketedRecord(
                            ordered.get(position),
                            bucket,
                            bucketCount
                        )
                    );

                    position++;
                }
            }

            return List.copyOf(result);
        }

        List<BucketStatistics> statistics(
            List<BucketedRecord> bucketed
        ) {
            Map<Integer, List<Double>> scores =
                new HashMap<>();

            for (BucketedRecord item : bucketed) {
                scores.computeIfAbsent(
                    item.bucket(),
                    ignored -> new ArrayList<>()
                ).add(item.record().score());
            }

            return scores.entrySet()
                .stream()
                .sorted(Map.Entry.comparingByKey())
                .map(entry -> {
                    List<Double> values = entry.getValue();

                    double minimum =
                        values.stream()
                            .mapToDouble(Double::doubleValue)
                            .min()
                            .orElseThrow();

                    double maximum =
                        values.stream()
                            .mapToDouble(Double::doubleValue)
                            .max()
                            .orElseThrow();

                    double average =
                        values.stream()
                            .mapToDouble(Double::doubleValue)
                            .average()
                            .orElseThrow();

                    return new BucketStatistics(
                        entry.getKey(),
                        values.size(),
                        minimum,
                        maximum,
                        average
                    );
                })
                .toList();
        }

        Map<Integer, String> segment(
            List<Record> records,
            BucketPolicy policy
        ) {
            List<BucketedRecord> bucketed =
                assign(records, 10);

            Map<Integer, String> result =
                new HashMap<>();

            for (BucketedRecord item : bucketed) {
                result.put(
                    item.record().id(),
                    policy.label(item.bucket())
                );
            }

            return Map.copyOf(result);
        }

        private void validateBucketCount(int bucketCount) {
            if (bucketCount <= 0) {
                throw new IllegalArgumentException(
                    "bucketCount must be positive"
                );
            }
        }
    }

    static void validateInvariants(
        List<Record> records,
        int bucketCount,
        NtileService service
    ) {
        List<BucketedRecord> result =
            service.assign(records, bucketCount);

        if (result.size() != records.size()) {
            throw new IllegalStateException(
                "NTILE changed the number of records"
            );
        }

        int[] sizes = new int[bucketCount + 1];

        for (BucketedRecord item : result) {
            sizes[item.bucket()]++;
        }

        int minimum = sizes[1];
        int maximum = sizes[1];

        for (int bucket = 1;
             bucket <= bucketCount;
             bucket++) {

            minimum = Math.min(minimum, sizes[bucket]);
            maximum = Math.max(maximum, sizes[bucket]);
        }

        if (!records.isEmpty() && maximum - minimum > 1) {
            throw new IllegalStateException(
                "NTILE buckets are not balanced"
            );
        }
    }

    public static void main(String[] args) {
        List<Record> records = List.of(
            new Record(101, "Asha", 96.0),
            new Record(102, "Bharat", 82.0),
            new Record(103, "Chirag", 91.0),
            new Record(104, "Divya", 74.0),
            new Record(105, "Esha", 88.0),
            new Record(106, "Farhan", 67.0),
            new Record(107, "Gita", 91.0),
            new Record(108, "Harsh", 59.0),
            new Record(109, "Isha", 84.0),
            new Record(110, "Jay", 72.0),
            new Record(111, "Kiran", 95.0),
            new Record(112, "Lalit", 63.0)
        );

        NtileService service = new NtileService();

        System.out.println("QUARTILES");

        List<BucketedRecord> quartiles =
            service.assign(
                records,
                SegmentationType.QUARTILE.bucketCount()
            );

        quartiles.forEach(item ->
            System.out.printf(
                "%s score=%.1f quartile=%d%n",
                item.record().customer(),
                item.record().score(),
                item.bucket()
            )
        );

        System.out.println("\nQUARTILE STATISTICS");

        service.statistics(quartiles).forEach(
            System.out::println
        );

        System.out.println("\nDECILES");

        List<BucketedRecord> deciles =
            service.assign(
                records,
                SegmentationType.DECILE.bucketCount()
            );

        deciles.forEach(item ->
            System.out.printf(
                "%s score=%.1f decile=%d%n",
                item.record().customer(),
                item.record().score(),
                item.bucket()
            )
        );

        System.out.println("\nSEGMENTS");

        Map<Integer, String> segments =
            service.segment(
                records,
                new DecilePolicy()
            );

        records.forEach(record ->
            System.out.println(
                record.id()
                    + " -> "
                    + segments.get(record.id())
            )
        );

        validateInvariants(records, 4, service);
        validateInvariants(records, 10, service);
        validateInvariants(List.of(), 5, service);

        System.out.println("\nNTILE validation passed.");
    }
}
