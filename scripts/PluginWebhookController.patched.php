<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Plugin;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;
use Illuminate\Validation\Rule;

class PluginWebhookController extends Controller
{
    public function __invoke(Request $request, Plugin $plugin): JsonResponse
    {
        if ($plugin->data_strategy !== 'webhook') {
            return response()->json(['error' => 'Plugin does not use webhook strategy'], 400);
        }

        if ($request->isMethod('get')) {
            return response()->json([
                'merge_variables' => $plugin->data_payload ?? [],
            ]);
        }

        if (! $request->has('merge_variables')) {
            return response()->json(['error' => 'Request must contain merge_variables key'], 400);
        }

        $validator = Validator::make(
            $request->all(),
            [
                'merge_strategy' => ['nullable', 'string', Rule::in(Plugin::webhookMergeStrategies())],
                'stream_limit' => ['nullable', 'integer', 'min' => 1],
            ],
            [
                'merge_strategy.in' => 'merge_strategy must be one of: deep_merge, stream',
                'stream_limit.integer' => 'stream_limit must be a positive integer',
                'stream_limit.min' => 'stream_limit must be a positive integer',
            ]
        );

        if ($validator->fails()) {
            return response()->json(['error' => $validator->errors()->first()], 400);
        }

        $mergeVariables = Plugin::mergeWebhookPayload(
            currentPayload: $plugin->data_payload,
            incomingPayload: $request->input('merge_variables'),
            mergeStrategy: $request->string('merge_strategy')->toString() ?: null,
            streamLimit: $request->has('stream_limit') ? (int) $request->input('stream_limit') : null,
        );

        if (! Plugin::dataPayloadWithinWireLimit($mergeVariables)) {
            return response()->json(Plugin::oversizedDataPayloadErrorPayload(), 413);
        }

        $updateData = [
            'data_payload' => $mergeVariables,
        ];

        // Preserve sidecar handoff: when a colour sidecar has already set
        // current_image, do NOT update data_payload_updated_at — that would
        // trigger isDataStale() for webhook plugins and cause LaraPaper to
        // re-render natively, overwriting the sidecar's higher-quality image.
        // The payload data is still updated so the sidecar can read fresh data.
        if (! str_starts_with($plugin->current_image ?? '', 'sidecar_')) {
            $updateData['data_payload_updated_at'] = now();
        }

        $plugin->update($updateData);

        return response()->json(['message' => 'Data updated successfully']);
    }
}
